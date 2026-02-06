#!/usr/bin/env python3
"""
Mega MU Scheduled Runner
Executes scheduled collections from the database
"""

import os
import sys
import time
import logging
from datetime import datetime
import subprocess
from dotenv import load_dotenv

try:
    import mysql.connector
except ImportError as e:
    print(f"Error: Missing required package - {e}")
    print("Install with: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduled_runner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class ScheduledRunner:
    """Executes scheduled collections from database"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def connect_db(self):
        """Connect to database"""
        try:
            self.conn = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD', ''),
                database=os.getenv('DB_NAME', 'mega_mu_trader')
            )
            self.cursor = self.conn.cursor(dictionary=True)
            logger.info("Database connection established")
            return True
        except mysql.connector.Error as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def disconnect_db(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def get_pending_collections(self):
        """Get collections that should be executed now"""
        query = """
            SELECT id, collection_type, scheduled_for
            FROM scheduled_collections
            WHERE status = 'pending'
            AND scheduled_for <= NOW()
            ORDER BY scheduled_for ASC
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def update_collection_status(self, collection_id, status, error_message=None):
        """Update collection status"""
        query = """
            UPDATE scheduled_collections
            SET status = %s,
                executed_at = NOW(),
                error_message = %s
            WHERE id = %s
        """
        self.cursor.execute(query, (status, error_message, collection_id))
        self.conn.commit()
    
    def execute_collection(self, collection):
        """Execute a collection"""
        collection_id = collection['id']
        collection_type = collection['collection_type']
        
        logger.info(f"Executing scheduled collection #{collection_id} ({collection_type})")
        
        # Update status to running
        self.update_collection_status(collection_id, 'running')
        
        try:
            # Execute the collection script
            result = subprocess.run(
                [sys.executable, 'hybrid_collector.py', '--mode', collection_type],
                capture_output=True,
                text=True,
                timeout=3600  # 60 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Collection #{collection_id} completed successfully")
                self.update_collection_status(collection_id, 'completed')
            else:
                error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                logger.error(f"✗ Collection #{collection_id} failed: {error_msg}")
                self.update_collection_status(collection_id, 'failed', error_msg)
                
        except subprocess.TimeoutExpired:
            error_msg = "Collection timed out (60 minutes)"
            logger.error(f"✗ Collection #{collection_id} timed out")
            self.update_collection_status(collection_id, 'failed', error_msg)
        except Exception as e:
            error_msg = str(e)[:500]
            logger.error(f"✗ Collection #{collection_id} error: {e}")
            self.update_collection_status(collection_id, 'failed', error_msg)
    
    def run(self):
        """Main run loop"""
        logger.info("=" * 60)
        logger.info("Mega MU Scheduled Runner Starting")
        logger.info("=" * 60)
        
        if not self.connect_db():
            logger.error("Failed to connect to database")
            return False
        
        try:
            while True:
                # Get pending collections
                pending = self.get_pending_collections()
                
                if pending:
                    logger.info(f"Found {len(pending)} pending collection(s)")
                    
                    for collection in pending:
                        self.execute_collection(collection)
                
                # Wait 60 seconds before checking again
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("\nScheduled runner stopped by user")
        finally:
            self.disconnect_db()


def main():
    """Main entry point"""
    runner = ScheduledRunner()
    runner.run()


if __name__ == "__main__":
    main()
