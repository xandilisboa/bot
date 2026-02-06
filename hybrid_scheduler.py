#!/usr/bin/env python3
"""
Mega MU Hybrid Scheduler
Schedules both selective and complete collections
"""

import schedule
import time
import logging
from datetime import datetime
import subprocess
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hybrid_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_selective_collection():
    """Run selective collection (items of interest only)"""
    logger.info("=" * 60)
    logger.info("STARTING SELECTIVE COLLECTION")
    logger.info("=" * 60)
    
    try:
        result = subprocess.run(
            [sys.executable, 'hybrid_collector.py', '--mode', 'selective'],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes timeout
        )
        
        if result.returncode == 0:
            logger.info("✓ Selective collection completed successfully")
            logger.info(result.stdout)
        else:
            logger.error(f"✗ Selective collection failed with code {result.returncode}")
            logger.error(result.stderr)
            
    except subprocess.TimeoutExpired:
        logger.error("✗ Selective collection timed out (30 minutes)")
    except Exception as e:
        logger.error(f"✗ Selective collection error: {e}")


def run_complete_collection():
    """Run complete collection (all items)"""
    logger.info("=" * 60)
    logger.info("STARTING COMPLETE COLLECTION")
    logger.info("=" * 60)
    
    try:
        result = subprocess.run(
            [sys.executable, 'hybrid_collector.py', '--mode', 'complete'],
            capture_output=True,
            text=True,
            timeout=3600  # 60 minutes timeout
        )
        
        if result.returncode == 0:
            logger.info("✓ Complete collection completed successfully")
            logger.info(result.stdout)
        else:
            logger.error(f"✗ Complete collection failed with code {result.returncode}")
            logger.error(result.stderr)
            
    except subprocess.TimeoutExpired:
        logger.error("✗ Complete collection timed out (60 minutes)")
    except Exception as e:
        logger.error(f"✗ Complete collection error: {e}")


def main():
    """Main scheduler loop"""
    logger.info("=" * 60)
    logger.info("Mega MU Scheduler Starting")
    logger.info("=" * 60)
    
    # Schedule COMPLETE collections (4x per day)
    schedule.every().day.at("05:00").do(run_complete_collection)
    schedule.every().day.at("10:00").do(run_complete_collection)
    schedule.every().day.at("17:00").do(run_complete_collection)
    schedule.every().day.at("23:00").do(run_complete_collection)
    
    logger.info("Schedule configured:")
    logger.info("  - Complete collections: 05:00, 10:00, 17:00, 23:00 (daily)")
    logger.info("")
    logger.info("Scheduler is now running. Press Ctrl+C to stop.")
    logger.info("=" * 60)
    
    # Run scheduler loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("\nScheduler stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
