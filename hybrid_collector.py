#!/usr/bin/env python3
"""
Mega MU Hybrid Market Collector
Implements hybrid collection strategy:
- Selective daily collection (4x/day): Only items of interest
- Complete weekly collection (1x/week): All items for trend analysis
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import json

try:
    import pyautogui
    import pytesseract
    from PIL import Image, ImageGrab
    import cv2
    import numpy as np
    import mysql.connector
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Missing required package - {e}")
    print("Install with: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hybrid_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
CONFIG = {
    'MARKET_KEY': 'p',  # Key to open market
    'TOOLTIP_DELAY': 1.5,  # Seconds to wait for tooltip to appear
    'CLICK_DELAY': 0.5,  # Delay between clicks
    'PAGE_LOAD_DELAY': 2.0,  # Delay for page to load
    'OCR_CONFIDENCE': 60,  # Minimum OCR confidence
    'SCREENSHOT_DIR': 'screenshots',
    'CALIBRATION_FILE': 'calibration.json',
}


class CoordinateManager:
    """Manages UI coordinates with calibration support"""
    
    def __init__(self, calibration_file: str):
        self.calibration_file = calibration_file
        self.coords = self.load_calibration()
    
    def load_calibration(self) -> Dict:
        """Load coordinates from calibration file"""
        if os.path.exists(self.calibration_file):
            with open(self.calibration_file, 'r') as f:
                data = json.load(f)
                # Handle new format from calibrate_macos.py
                if 'coordinates' in data:
                    coords = data['coordinates']
                    self.retina_scale = data.get('retina_scale', 1)
                    # Map calibrate_macos names to expected names
                    return {
                        'next_page_button': coords.get('next_page_button', {'x': 435, 'y': 810}),
                        'prev_page_button': coords.get('prev_page_button', {'x': 365, 'y': 810}),
                        'close_shop_button': coords.get('close_shop_button', {'x': 455, 'y': 472}),
                        'first_shop': coords.get('first_shop', {'x': 300, 'y': 400}),
                        'first_item_slot': coords.get('first_item_slot', {'x': 200, 'y': 600}),
                        'retina_scale': self.retina_scale,
                    }
                return data
        
        # Default coordinates (need to be calibrated)
        return {
            'next_page_button': {'x': 435, 'y': 810},
            'prev_page_button': {'x': 365, 'y': 810},
            'close_shop_button': {'x': 455, 'y': 472},
            'first_shop': {'x': 300, 'y': 400},
            'first_item_slot': {'x': 200, 'y': 600},
            'retina_scale': 1,
        }
    
    def save_calibration(self):
        """Save current coordinates to file"""
        with open(self.calibration_file, 'w') as f:
            json.dump(self.coords, f, indent=2)
        logger.info(f"Calibration saved to {self.calibration_file}")
    
    def calibrate(self):
        """Interactive calibration mode"""
        logger.info("=" * 60)
        logger.info("CALIBRATION MODE")
        logger.info("=" * 60)
        logger.info("Move your mouse to each position and press SPACE")
        logger.info("Press ESC to finish calibration")
        
        positions = [
            ('next_page_button', 'Next page button (arrow →)'),
            ('prev_page_button', 'Previous page button (arrow ←)'),
            ('close_shop_button', 'Close shop button (X)'),
        ]
        
        for key, description in positions:
            logger.info(f"\nPosition mouse over: {description}")
            logger.info("Press SPACE when ready...")
            
            while True:
                if pyautogui.keyDown('space'):
                    pos = pyautogui.position()
                    self.coords[key] = {'x': pos.x, 'y': pos.y}
                    logger.info(f"✓ Saved: {key} = ({pos.x}, {pos.y})")
                    time.sleep(0.5)
                    break
                elif pyautogui.keyDown('esc'):
                    logger.info("Calibration cancelled")
                    return
                time.sleep(0.1)
        
        self.save_calibration()
        logger.info("\n✓ Calibration complete!")


class TooltipDetector:
    """Detects and captures item tooltips using computer vision"""
    
    def __init__(self, screenshot_dir: str):
        self.screenshot_dir = screenshot_dir
        os.makedirs(screenshot_dir, exist_ok=True)
    
    def capture_screen(self) -> Image.Image:
        """Capture current screen"""
        return ImageGrab.grab()
    
    def detect_tooltip(self, image: Image.Image) -> Optional[Tuple[int, int, int, int]]:
        """
        Detect tooltip window in image using color detection
        Returns: (x, y, width, height) or None
        """
        # Convert to numpy array
        img_np = np.array(image)
        
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
        
        # Define range for dark blue tooltip background
        # Adjust these values based on actual tooltip color
        lower_blue = np.array([100, 50, 20])
        upper_blue = np.array([130, 255, 100])
        
        # Create mask
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # Find largest contour (likely the tooltip)
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Filter by size (tooltip should be reasonably sized)
        if w < 100 or h < 100 or w > 800 or h > 600:
            return None
        
        return (x, y, w, h)
    
    def extract_tooltip_text(self, image: Image.Image, bbox: Tuple[int, int, int, int]) -> Dict:
        """Extract text from tooltip using OCR"""
        x, y, w, h = bbox
        
        # Crop tooltip area
        tooltip_img = image.crop((x, y, x + w, y + h))
        
        # Save for debugging
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        tooltip_path = os.path.join(self.screenshot_dir, f'tooltip_{timestamp}.png')
        tooltip_img.save(tooltip_path)
        
        # Enhance image for better OCR
        tooltip_np = np.array(tooltip_img)
        gray = cv2.cvtColor(tooltip_np, cv2.COLOR_RGB2GRAY)
        
        # Apply threshold
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # OCR
        text = pytesseract.image_to_string(binary, config='--psm 6')
        
        # Parse tooltip data
        data = self.parse_tooltip_text(text)
        data['screenshot'] = tooltip_path
        
        return data
    
    def parse_tooltip_text(self, text: str) -> Dict:
        """Parse tooltip text to extract item data"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        data = {
            'item_name': None,
            'price': None,
            'quantity': None,
            'attributes': [],
            'raw_text': text,
        }
        
        if not lines:
            return data
        
        # First line is usually the item name
        data['item_name'] = lines[0]
        
        # Look for price
        for line in lines:
            if 'price' in line.lower() or 'zen' in line.lower() or 'mc' in line.lower():
                # Extract numbers
                import re
                numbers = re.findall(r'[\d,.]+', line)
                if numbers:
                    # Remove dots/commas and convert to int
                    price_str = numbers[-1].replace('.', '').replace(',', '')
                    try:
                        data['price'] = int(price_str)
                    except ValueError:
                        pass
            
            if 'quantidade' in line.lower() or 'quantity' in line.lower():
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    data['quantity'] = int(numbers[0])
            
            # Store other attributes
            if line and line not in [data['item_name']]:
                data['attributes'].append(line)
        
        return data


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = mysql.connector.connect(
                host=os.getenv('DATABASE_HOST', 'localhost'),
                port=int(os.getenv('DATABASE_PORT', '3306')),
                user=os.getenv('DATABASE_USER', 'root'),
                password=os.getenv('DATABASE_PASSWORD', ''),
                database=os.getenv('DATABASE_NAME', 'mega_mu_trader'),
                ssl_ca=None,
                ssl_disabled=False
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
    
    def get_items_of_interest(self) -> List[str]:
        """Get list of items to monitor"""
        query = "SELECT DISTINCT item_name FROM items_of_interest WHERE is_active = 1"
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        return [row['item_name'] for row in results]
    
    def save_item_data(self, seller: str, item_data: Dict, collection_log_id: int):
        """Save collected item data to database"""
        try:
            # Insert or update seller
            seller_query = """
                INSERT INTO sellers (seller_name, first_seen, last_seen)
                VALUES (%s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE last_seen = NOW()
            """
            self.cursor.execute(seller_query, (seller,))
            
            # Get seller_id
            self.cursor.execute("SELECT id FROM sellers WHERE seller_name = %s", (seller,))
            seller_id = self.cursor.fetchone()['id']
            
            # Insert or update market item
            item_query = """
                INSERT INTO market_items (item_name, seller_id, last_seen)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE last_seen = NOW(), seller_id = %s
            """
            self.cursor.execute(item_query, (item_data['item_name'], seller_id, seller_id))
            
            # Get item_id
            self.cursor.execute(
                "SELECT id FROM market_items WHERE item_name = %s AND seller_id = %s",
                (item_data['item_name'], seller_id)
            )
            item_id = self.cursor.fetchone()['id']
            
            # Insert price history
            price_query = """
                INSERT INTO price_history 
                (item_id, seller_id, item_name, seller_name, price_text, price_numeric, 
                 quantity, attributes, screenshot_path, collection_log_id, collected_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            attributes_json = json.dumps(item_data.get('attributes', []))
            
            self.cursor.execute(price_query, (
                item_id,
                seller_id,
                item_data['item_name'],
                seller,
                str(item_data.get('price', '')),
                item_data.get('price'),
                item_data.get('quantity'),
                attributes_json,
                item_data.get('screenshot'),
                collection_log_id
            ))
            
            self.conn.commit()
            logger.info(f"✓ Saved: {seller} - {item_data['item_name']} - {item_data.get('price', 'N/A')}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving item data: {e}")
            self.conn.rollback()
            return False
    
    def create_collection_log(self, collection_type: str) -> int:
        """Create a new collection log entry"""
        query = """
            INSERT INTO collection_logs 
            (collection_type, status, started_at)
            VALUES (%s, 'running', NOW())
        """
        self.cursor.execute(query, (collection_type,))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_collection_log(self, log_id: int, pages: int, items: int, status: str, error: str = None):
        """Update collection log with results"""
        query = """
            UPDATE collection_logs
            SET pages_scanned = %s,
                items_collected = %s,
                status = %s,
                error_message = %s,
                completed_at = NOW()
            WHERE id = %s
        """
        self.cursor.execute(query, (pages, items, status, error, log_id))
        self.conn.commit()


class HybridCollector:
    """Main hybrid collector class"""
    
    def __init__(self):
        self.coords = CoordinateManager(CONFIG['CALIBRATION_FILE'])
        self.tooltip_detector = TooltipDetector(CONFIG['SCREENSHOT_DIR'])
        self.db = DatabaseManager()
        self.items_collected = 0
        self.pages_scanned = 0
    
    def open_market(self) -> bool:
        """Open market window"""
        logger.info("Opening market...")
        pyautogui.press(CONFIG['MARKET_KEY'])
        time.sleep(CONFIG['PAGE_LOAD_DELAY'])
        return True
    
    def click_shop(self, shop_index: int = 0) -> bool:
        """Click on a shop in the list"""
        # Use first_shop position and add offset for each shop (assuming ~40px spacing)
        first_shop = self.coords.coords['first_shop']
        x = first_shop['x']
        y = first_shop['y'] + (shop_index * 40)  # Adjust spacing as needed
        logger.info(f"Clicking shop at position: X={x}, Y={y}")
        pyautogui.click(x, y)
        time.sleep(CONFIG['PAGE_LOAD_DELAY'])
        return True
    
    def close_shop(self):
        """Close current shop window"""
        coords = self.coords.coords['close_shop_button']
        pyautogui.click(coords['x'], coords['y'])
        time.sleep(CONFIG['CLICK_DELAY'])
    
    def next_page(self) -> bool:
        """Go to next page"""
        coords = self.coords.coords['next_page_button']
        pyautogui.click(coords['x'], coords['y'])
        time.sleep(CONFIG['PAGE_LOAD_DELAY'])
        self.pages_scanned += 1
        return True
    
    def scan_shop_grid(self, seller_name: str, collection_log_id: int, items_of_interest: List[str] = None):
        """
        Scan shop grid by moving mouse over each slot
        Detects multi-slot items to avoid duplicates
        """
        first_slot = self.coords.coords['first_item_slot']
        retina_scale = self.coords.coords.get('retina_scale', 2)
        
        # Grid: 8 columns x 4 rows = 32 slots, touching (no spacing)
        rows = 4
        cols = 8
        
        # Calculate slot_size based on Retina scale
        # For Retina displays, coordinates are already scaled, so use smaller slot size
        slot_size = 32 if retina_scale == 2 else 40
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Scanning shop: {seller_name}")
        logger.info(f"Grid: {cols}x{rows}={cols*rows} slots")
        logger.info(f"First slot: ({first_slot['x']},{first_slot['y']})")
        logger.info(f"Slot size: {slot_size}px (Retina scale: {retina_scale})")
        logger.info(f"{'='*60}")
        
        # Track items to avoid duplicates
        items_seen = set()
        tooltips_found = 0
        
        for row in range(rows):
            for col in range(cols):
                slot_num = row * cols + col + 1
                x = first_slot['x'] + (col * slot_size)
                y = first_slot['y'] + (row * slot_size)
                
                logger.info(f"[Slot {slot_num:2d}/{cols*rows}] Moving to ({x:4d},{y:4d})...")
                pyautogui.moveTo(x, y, duration=0.15)
                time.sleep(CONFIG['TOOLTIP_DELAY'])
                
                # Capture screen
                screen = self.tooltip_detector.capture_screen()
                
                # Detect tooltip
                tooltip_bbox = self.tooltip_detector.detect_tooltip(screen)
                
                if tooltip_bbox:
                    tooltips_found += 1
                    logger.info(f"  ✓ Tooltip detected at slot {slot_num}")
                    
                    # Extract tooltip data
                    item_data = self.tooltip_detector.extract_tooltip_text(screen, tooltip_bbox)
                    item_name = item_data.get('item_name', '')
                    item_price = item_data.get('price', 0)
                    
                    logger.info(f"  → Item: {item_name} | Price: {item_price}")
                    
                    # Skip if we already collected this item (multi-slot detection)
                    item_key = f"{item_name}_{item_price}"
                    if item_key in items_seen:
                        logger.info(f"  ⊗ Duplicate (multi-slot item)")
                        continue
                    
                    # Check if item is of interest (selective mode)
                    if items_of_interest:
                        if not any(interest.lower() in item_name.lower() 
                                 for interest in items_of_interest):
                            logger.info(f"  ⊘ Not in interest list")
                            continue
                    
                    # Save to database
                    if self.db.save_item_data(seller_name, item_data, collection_log_id):
                        self.items_collected += 1
                        items_seen.add(item_key)
                        logger.info(f"  ✓✓ COLLECTED!")
                else:
                    logger.debug(f"  ✗ No tooltip at slot {slot_num}")
                
                # Small delay between slots
                time.sleep(0.1)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Shop scan complete: {len(items_seen)} unique items collected")
        logger.info(f"Tooltips detected: {tooltips_found}/{cols*rows} slots")
        logger.info(f"{'='*60}\n")

    
    
    def scroll_shop_list(self, scrolls: int = 1, direction: str = 'down'):
        """Scroll the shop list to access more shops"""
        first_shop = self.coords.coords['first_shop']
        # Position mouse over shop list area
        pyautogui.moveTo(first_shop['x'], first_shop['y'])
        time.sleep(0.2)
        
        # Scroll (negative for down, positive for up)
        scroll_amount = -3 if direction == 'down' else 3
        for _ in range(scrolls):
            pyautogui.scroll(scroll_amount)
            time.sleep(0.3)
        
        logger.info(f"Scrolled shop list {direction} {scrolls} times")
    
    def collect_selective(self, log_id: int):
        """Selective collection - only items of interest"""
        logger.info("Starting SELECTIVE collection...")
        
        items_of_interest = self.db.get_items_of_interest()
        logger.info(f"Monitoring {len(items_of_interest)} items: {items_of_interest}")
        
        if not items_of_interest:
            logger.warning("No items of interest configured. Skipping selective collection.")
            return
        
        # Open market
        self.open_market()
        
        # Configuration: how many shops to scan
        shops_per_screen = 5  # Visible shops without scrolling
        total_shops_to_scan = 20  # Scan first 20 shops (adjust as needed)
        scroll_every = shops_per_screen  # Scroll after checking all visible shops
        
        logger.info(f"Will scan {total_shops_to_scan} shops total")
        
        shops_scanned = 0
        for batch in range(total_shops_to_scan // shops_per_screen):
            logger.info(f"\n--- Batch {batch + 1}: Shops {shops_scanned + 1}-{shops_scanned + shops_per_screen} ---")
            
            # Scan visible shops
            for shop_index in range(shops_per_screen):
                shops_scanned += 1
                logger.info(f"\nScanning shop {shops_scanned}/{total_shops_to_scan}...")
                
                try:
                    # Click on shop
                    self.click_shop(shop_index)
                    time.sleep(1.5)  # Wait for shop to open
                    
                    # Scan shop grid for items of interest
                    self.scan_shop_grid(f"Shop_{shops_scanned}", log_id, items_of_interest)
                    
                    # Close shop
                    self.close_shop()
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error scanning shop {shops_scanned}: {e}")
                    continue
            
            # Scroll down to see more shops (unless this is the last batch)
            if shops_scanned < total_shops_to_scan:
                logger.info("\nScrolling to next batch of shops...")
                self.scroll_shop_list(scrolls=2, direction='down')
                time.sleep(1.0)
        
        logger.info("Selective collection completed")
    
    def collect_complete(self, log_id: int):
        """Complete collection - all items"""
        logger.info("Starting COMPLETE collection...")
        
        # Open market
        self.open_market()
        
        # TODO: Implement complete scanning logic
        logger.info("Complete collection completed")
    
    def run(self, collection_type: str = 'selective'):
        """Main collection run"""
        logger.info("=" * 60)
        logger.info(f"Mega MU Hybrid Collector - {collection_type.upper()} MODE")
        logger.info("=" * 60)
        
        if not self.db.connect():
            logger.error("Failed to connect to database")
            return False
        
        try:
            # Create collection log
            log_id = self.db.create_collection_log(collection_type)
            
            # Run collection
            if collection_type == 'selective':
                self.collect_selective(log_id)
            else:
                self.collect_complete(log_id)
            
            # Update log
            self.db.update_collection_log(
                log_id,
                self.pages_scanned,
                self.items_collected,
                'completed'
            )
            
            logger.info(f"✓ Collection complete: {self.items_collected} items from {self.pages_scanned} pages")
            return True
            
        except Exception as e:
            logger.error(f"Collection failed: {e}")
            self.db.update_collection_log(log_id, self.pages_scanned, self.items_collected, 'failed', str(e))
            return False
        finally:
            self.db.disconnect()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mega MU Hybrid Market Collector')
    parser.add_argument('--mode', choices=['selective', 'complete', 'calibrate'], 
                       default='selective', help='Collection mode')
    args = parser.parse_args()
    
    collector = HybridCollector()
    
    if args.mode == 'calibrate':
        collector.coords.calibrate()
    else:
        collector.run(collection_type=args.mode)


if __name__ == "__main__":
    main()
