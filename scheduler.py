"""
Scheduler for automatic flight data scraping
Runs the scraper at regular intervals
"""

import logging
import schedule
import time
from datetime import datetime
import os

from flight_scraper import AirNZFlightScraper
from config import SCRAPE_INTERVAL_HOURS, LOG_DIR, LOG_FILE, LOG_LEVEL

# Setup logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, LOG_FILE)),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def scheduled_scrape():
    """Execute the scheduled scrape"""
    logger.info(f"Starting scheduled scrape at {datetime.now()}")
    
    scraper = None
    try:
        scraper = AirNZFlightScraper()
        all_flights = scraper.scrape_all_routes()
        scraper.save_to_csv()
        scraper.save_to_json()
        
        logger.info(f"Scheduled scrape completed. Found {len(all_flights)} flights")
    except Exception as e:
        logger.error(f"Error in scheduled scrape: {e}")
    finally:
        if scraper:
            scraper.close()


def start_scheduler():
    """Start the scheduler"""
    logger.info(f"Scheduler started. Running scrape every {SCRAPE_INTERVAL_HOURS} hours")
    
    # Schedule the job
    schedule.every(SCRAPE_INTERVAL_HOURS).hours.do(scheduled_scrape)
    
    # Run the first scrape immediately
    scheduled_scrape()
    
    # Keep the scheduler running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")


if __name__ == "__main__":
    start_scheduler()