#!/usr/bin/env python3
"""
Scheduler for Mega MU Market Collector
Runs collection at configured times: 5h, 10h, 17h, 23h
"""

import os
import sys
import time
import logging
import schedule
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from market_collector import MarketCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Collection schedule (24-hour format)
COLLECTION_HOURS = [5, 10, 17, 23]


def run_collection_job():
    """Job function to run market collection"""
    logger.info("=" * 60)
    logger.info(f"Starting scheduled collection at {datetime.now()}")
    logger.info("=" * 60)
    
    try:
        collector = MarketCollector()
        success = collector.run_collection()
        
        if success:
            logger.info("Scheduled collection completed successfully")
        else:
            logger.error("Scheduled collection failed")
    except Exception as e:
        logger.error(f"Scheduled collection error: {e}")


def setup_schedule():
    """Setup collection schedule"""
    for hour in COLLECTION_HOURS:
        time_str = f"{hour:02d}:00"
        schedule.every().day.at(time_str).do(run_collection_job)
        logger.info(f"Scheduled collection at {time_str}")


def main():
    """Main scheduler loop"""
    logger.info("=" * 60)
    logger.info("Mega MU Market Collector Scheduler Starting")
    logger.info("=" * 60)
    
    # Setup schedule
    setup_schedule()
    
    logger.info("Scheduler is running. Press Ctrl+C to stop.")
    logger.info(f"Next collection times: {COLLECTION_HOURS}")
    
    # Run scheduler loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
