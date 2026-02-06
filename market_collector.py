#!/usr/bin/env python3
"""
Mega MU Market Collector Bot
Automates market data collection using PyAutoGUI and Tesseract OCR
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re

try:
    import pyautogui
    import pytesseract
    from PIL import Image
    import mysql.connector
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Missing required package - {e}")
    print("Please install: pip install pyautogui pytesseract pillow mysql-connector-python python-dotenv")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('market_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
class Config:
    # Market navigation
    MARKET_KEY = 'p'  # Key to open market
    SCREENSHOT_DELAY = 2  # Seconds between screenshots
    PAGE_NAVIGATION_DELAY = 1  # Seconds between page navigation
    MAX_PAGES = 100  # Maximum pages to scan (safety limit)
    
    # OCR settings
    OCR_CONFIDENCE_THRESHOLD = 60
    TESSERACT_CONFIG = '--psm 6 --oem 3'  # Page segmentation mode
    
    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 5
    
    # Paths
    SCREENSHOTS_DIR = Path(__file__).parent / 'screenshots'
    
    # Database
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'mega_mu_trader')
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories"""
        cls.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.collection_run_id = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = mysql.connector.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME
            )
            self.cursor = self.conn.cursor(dictionary=True)
            logger.info("Database connection established")
            return True
        except mysql.connector.Error as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")
    
    def start_collection_run(self) -> Optional[int]:
        """Start a new collection run and return its ID"""
        try:
            query = """
                INSERT INTO collection_logs (started_at, status, items_collected, pages_scanned, errors_count)
                VALUES (NOW(), 'running', 0, 0, 0)
            """
            self.cursor.execute(query)
            self.conn.commit()
            self.collection_run_id = self.cursor.lastrowid
            logger.info(f"Started collection run #{self.collection_run_id}")
            return self.collection_run_id
        except mysql.connector.Error as e:
            logger.error(f"Failed to start collection run: {e}")
            return None
    
    def update_collection_run(self, status: str, items_collected: int, pages_scanned: int, 
                             errors_count: int, error_message: Optional[str] = None):
        """Update collection run status"""
        try:
            query = """
                UPDATE collection_logs 
                SET completed_at = NOW(), status = %s, items_collected = %s, 
                    pages_scanned = %s, errors_count = %s, error_message = %s
                WHERE id = %s
            """
            self.cursor.execute(query, (status, items_collected, pages_scanned, 
                                       errors_count, error_message, self.collection_run_id))
            self.conn.commit()
            logger.info(f"Updated collection run #{self.collection_run_id}: {status}")
        except mysql.connector.Error as e:
            logger.error(f"Failed to update collection run: {e}")
    
    def insert_price_data(self, item_name: str, seller_name: str, price: str, 
                         price_numeric: Optional[int], status: Optional[str]):
        """Insert price data into database"""
        try:
            query = """
                INSERT INTO price_history 
                (item_name, seller_name, price, price_numeric, status, collected_at, collection_run_id)
                VALUES (%s, %s, %s, %s, %s, NOW(), %s)
            """
            self.cursor.execute(query, (item_name, seller_name, price, price_numeric, 
                                       status, self.collection_run_id))
            self.conn.commit()
        except mysql.connector.Error as e:
            logger.error(f"Failed to insert price data: {e}")
            raise
    
    def upsert_market_item(self, item_name: str):
        """Insert or update market item"""
        try:
            query = """
                INSERT INTO market_items (item_name, first_seen, last_seen)
                VALUES (%s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE last_seen = NOW()
            """
            self.cursor.execute(query, (item_name,))
            self.conn.commit()
        except mysql.connector.Error as e:
            logger.error(f"Failed to upsert market item: {e}")
    
    def upsert_seller(self, seller_name: str):
        """Insert or update seller"""
        try:
            query = """
                INSERT INTO sellers (seller_name, first_seen, last_seen, total_listings)
                VALUES (%s, NOW(), NOW(), 1)
                ON DUPLICATE KEY UPDATE last_seen = NOW(), total_listings = total_listings + 1
            """
            self.cursor.execute(query, (seller_name,))
            self.conn.commit()
        except mysql.connector.Error as e:
            logger.error(f"Failed to upsert seller: {e}")


class OCRProcessor:
    """Handles OCR processing of screenshots"""
    
    @staticmethod
    def extract_text_from_image(image_path: Path) -> str:
        """Extract text from image using Tesseract OCR"""
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, config=Config.TESSERACT_CONFIG)
            return text
        except Exception as e:
            logger.error(f"OCR failed for {image_path}: {e}")
            return ""
    
    @staticmethod
    def parse_market_data(text: str) -> List[Dict[str, str]]:
        """Parse market data from OCR text"""
        items = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            # Try to parse line format: "SellerName    Price/Status"
            # Examples:
            # "PARADOX666    :MC STORE:"
            # "ChinuChinu    1111"
            # "2Wbows    BOX SILVER OPEN"
            
            parts = re.split(r'\s{2,}', line)  # Split by 2+ spaces
            
            if len(parts) >= 2:
                seller_name = parts[0].strip()
                price_or_status = parts[1].strip()
                
                # Try to extract numeric price
                price_numeric = None
                price_match = re.search(r'\d+', price_or_status)
                if price_match:
                    try:
                        price_numeric = int(price_match.group())
                    except ValueError:
                        pass
                
                items.append({
                    'seller_name': seller_name,
                    'price': price_or_status,
                    'price_numeric': price_numeric,
                    'status': price_or_status if not price_numeric else None
                })
        
        return items


class MarketCollector:
    """Main market collector bot"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.ocr = OCRProcessor()
        self.screenshots_taken = []
        self.items_collected = 0
        self.pages_scanned = 0
        self.errors_count = 0
        Config.ensure_directories()
    
    def open_market(self) -> bool:
        """Open the market interface in game"""
        try:
            logger.info("Opening market interface...")
            pyautogui.press(Config.MARKET_KEY)
            time.sleep(Config.SCREENSHOT_DELAY)
            return True
        except Exception as e:
            logger.error(f"Failed to open market: {e}")
            return False
    
    def take_screenshot(self, page_num: int) -> Optional[Path]:
        """Take screenshot of current market page"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"market_page_{page_num}_{timestamp}.png"
            filepath = Config.SCREENSHOTS_DIR / filename
            
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            
            logger.info(f"Screenshot saved: {filename}")
            self.screenshots_taken.append(filepath)
            return filepath
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            self.errors_count += 1
            return None
    
    def navigate_next_page(self) -> bool:
        """Navigate to next market page"""
        try:
            # Look for "next" arrow button (right arrow)
            # This is a placeholder - you'll need to adjust coordinates based on actual game UI
            # Option 1: Click at specific coordinates
            # pyautogui.click(x=XXX, y=YYY)
            
            # Option 2: Use keyboard navigation if available
            pyautogui.press('right')
            
            time.sleep(Config.PAGE_NAVIGATION_DELAY)
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to next page: {e}")
            return False
    
    def detect_last_page(self, screenshot_path: Path) -> bool:
        """Detect if we're on the last page by checking pagination text"""
        try:
            # Extract text and look for pagination indicator like "4/4"
            text = self.ocr.extract_text_from_image(screenshot_path)
            
            # Look for pattern like "X/X" where both numbers are the same
            pagination_match = re.search(r'(\d+)\s*/\s*(\d+)', text)
            if pagination_match:
                current_page = int(pagination_match.group(1))
                total_pages = int(pagination_match.group(2))
                logger.info(f"Pagination detected: {current_page}/{total_pages}")
                return current_page >= total_pages
            
            return False
        except Exception as e:
            logger.error(f"Failed to detect last page: {e}")
            return False
    
    def process_screenshot(self, screenshot_path: Path) -> int:
        """Process screenshot and extract market data"""
        try:
            logger.info(f"Processing screenshot: {screenshot_path.name}")
            
            # Extract text using OCR
            text = self.ocr.extract_text_from_image(screenshot_path)
            
            if not text:
                logger.warning("No text extracted from screenshot")
                return 0
            
            # Parse market data
            items = self.ocr.parse_market_data(text)
            
            if not items:
                logger.warning("No items parsed from text")
                return 0
            
            # Save to database
            items_saved = 0
            for item in items:
                try:
                    # Use seller name as item name for now
                    # You may need to adjust this based on actual data structure
                    item_name = item['seller_name']
                    
                    self.db.insert_price_data(
                        item_name=item_name,
                        seller_name=item['seller_name'],
                        price=item['price'],
                        price_numeric=item['price_numeric'],
                        status=item['status']
                    )
                    
                    self.db.upsert_market_item(item_name)
                    self.db.upsert_seller(item['seller_name'])
                    
                    items_saved += 1
                except Exception as e:
                    logger.error(f"Failed to save item data: {e}")
                    self.errors_count += 1
            
            logger.info(f"Saved {items_saved} items from screenshot")
            return items_saved
            
        except Exception as e:
            logger.error(f"Failed to process screenshot: {e}")
            self.errors_count += 1
            return 0
    
    def run_collection(self) -> bool:
        """Run a complete market data collection"""
        try:
            # Connect to database
            if not self.db.connect():
                return False
            
            # Start collection run
            if not self.db.start_collection_run():
                return False
            
            # Open market
            if not self.open_market():
                self.db.update_collection_run('failed', 0, 0, 1, "Failed to open market")
                return False
            
            # Collect data from all pages
            page_num = 1
            while page_num <= Config.MAX_PAGES:
                logger.info(f"Scanning page {page_num}...")
                
                # Take screenshot
                screenshot_path = self.take_screenshot(page_num)
                if not screenshot_path:
                    break
                
                self.pages_scanned += 1
                
                # Process screenshot
                items_found = self.process_screenshot(screenshot_path)
                self.items_collected += items_found
                
                # Check if last page
                if self.detect_last_page(screenshot_path):
                    logger.info("Reached last page")
                    break
                
                # Navigate to next page
                if not self.navigate_next_page():
                    break
                
                page_num += 1
            
            # Update collection run status
            status = 'completed' if self.errors_count == 0 else 'partial'
            self.db.update_collection_run(
                status=status,
                items_collected=self.items_collected,
                pages_scanned=self.pages_scanned,
                errors_count=self.errors_count
            )
            
            logger.info(f"Collection completed: {self.items_collected} items from {self.pages_scanned} pages")
            return True
            
        except Exception as e:
            logger.error(f"Collection failed: {e}")
            self.db.update_collection_run('failed', self.items_collected, 
                                         self.pages_scanned, self.errors_count, str(e))
            return False
        finally:
            self.db.disconnect()


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Mega MU Market Collector Bot Starting")
    logger.info("=" * 60)
    
    collector = MarketCollector()
    success = collector.run_collection()
    
    if success:
        logger.info("Collection completed successfully")
        sys.exit(0)
    else:
        logger.error("Collection failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
