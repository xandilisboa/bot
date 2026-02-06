#!/usr/bin/env python3
"""
Mega MU Market Analyzer
Analyzes price data and detects arbitrage opportunities
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

try:
    import mysql.connector
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Missing required package - {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
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
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def get_latest_prices_by_item(self) -> Dict[str, List[Dict]]:
        """Get latest prices for each item grouped by item name"""
        query = """
            SELECT 
                item_name,
                seller_name,
                price_numeric,
                collected_at
            FROM price_history
            WHERE price_numeric IS NOT NULL
                AND collected_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY item_name, collected_at DESC
        """
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        
        # Group by item name
        items_dict = defaultdict(list)
        for row in results:
            items_dict[row['item_name']].append(row)
        
        return dict(items_dict)
    
    def insert_arbitrage_opportunity(self, item_name: str, lowest_price: int, 
                                    highest_price: int, lowest_seller: str, 
                                    highest_seller: str):
        """Insert arbitrage opportunity"""
        price_diff = highest_price - lowest_price
        profit_margin = int((price_diff / lowest_price) * 100) if lowest_price > 0 else 0
        
        query = """
            INSERT INTO arbitrage_opportunities 
            (item_name, lowest_price, highest_price, price_difference, 
             profit_margin, lowest_seller, highest_seller, detected_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), 1)
        """
        self.cursor.execute(query, (
            item_name, lowest_price, highest_price, price_diff,
            profit_margin, lowest_seller, highest_seller
        ))
        self.conn.commit()
        logger.info(f"Arbitrage opportunity detected: {item_name} - {profit_margin}% margin")
    
    def deactivate_old_opportunities(self, hours: int = 24):
        """Deactivate old arbitrage opportunities"""
        query = """
            UPDATE arbitrage_opportunities
            SET is_active = 0
            WHERE detected_at < DATE_SUB(NOW(), INTERVAL %s HOUR)
                AND is_active = 1
        """
        self.cursor.execute(query, (hours,))
        self.conn.commit()
        logger.info(f"Deactivated opportunities older than {hours} hours")


class ArbitrageAnalyzer:
    """Analyzes market data for arbitrage opportunities"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.min_profit_margin = 10  # Minimum 10% profit margin
        self.min_price_difference = 100  # Minimum price difference
    
    def analyze_item_prices(self, item_name: str, prices: List[Dict]) -> Optional[Dict]:
        """Analyze prices for a single item"""
        if len(prices) < 2:
            return None
        
        # Get unique prices from different sellers
        seller_prices = {}
        for price_data in prices:
            seller = price_data['seller_name']
            price = price_data['price_numeric']
            
            if seller not in seller_prices:
                seller_prices[seller] = price
        
        if len(seller_prices) < 2:
            return None
        
        # Find lowest and highest prices
        min_seller = min(seller_prices, key=seller_prices.get)
        max_seller = max(seller_prices, key=seller_prices.get)
        
        min_price = seller_prices[min_seller]
        max_price = seller_prices[max_seller]
        
        price_diff = max_price - min_price
        
        if price_diff < self.min_price_difference:
            return None
        
        profit_margin = (price_diff / min_price) * 100 if min_price > 0 else 0
        
        if profit_margin < self.min_profit_margin:
            return None
        
        return {
            'item_name': item_name,
            'lowest_price': min_price,
            'highest_price': max_price,
            'lowest_seller': min_seller,
            'highest_seller': max_seller,
            'price_difference': price_diff,
            'profit_margin': profit_margin
        }
    
    def run_analysis(self):
        """Run arbitrage analysis on all items"""
        logger.info("Starting arbitrage analysis...")
        
        # Get latest prices
        items_prices = self.db.get_latest_prices_by_item()
        
        opportunities_found = 0
        
        for item_name, prices in items_prices.items():
            opportunity = self.analyze_item_prices(item_name, prices)
            
            if opportunity:
                self.db.insert_arbitrage_opportunity(
                    item_name=opportunity['item_name'],
                    lowest_price=opportunity['lowest_price'],
                    highest_price=opportunity['highest_price'],
                    lowest_seller=opportunity['lowest_seller'],
                    highest_seller=opportunity['highest_seller']
                )
                opportunities_found += 1
        
        # Deactivate old opportunities
        self.db.deactivate_old_opportunities()
        
        logger.info(f"Analysis complete. Found {opportunities_found} new opportunities")
        return opportunities_found


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Mega MU Market Analyzer Starting")
    logger.info("=" * 60)
    
    db = DatabaseManager()
    
    if not db.connect():
        logger.error("Failed to connect to database")
        sys.exit(1)
    
    try:
        analyzer = ArbitrageAnalyzer(db)
        opportunities = analyzer.run_analysis()
        
        logger.info(f"Analysis completed successfully. Found {opportunities} opportunities")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()
