import logging
from playwright.sync_api import sync_playwright
from datetime import datetime
import time
from dotenv import load_dotenv

from scraper.ufc_stats_scraper import UFCStatsScraper

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_historical_scrape():
    logger.info("Starting one-off historical UFC scraper job...")
    start_time = datetime.now()
    scraper = UFCStatsScraper()
    
    try:
        with sync_playwright() as p:
            # Scrape All Completed Events
            completed_events = scraper.scrape_events(p, scraper.completed_url, "COMPLETED")
            logger.info(f"Scraped {len(completed_events)} historical events.")
            
            # For demonstration, we'll process them in reverse chronological order
            fights_updated = 0
            
            for idx, event in enumerate(completed_events):
                logger.info(f"Processing event {idx + 1}/{len(completed_events)}: {event['name']}")
                
                # Post the event
                saved_events = scraper.api_client.post_events([event])
                db_event_id = None
                if saved_events and isinstance(saved_events, list) and len(saved_events) > 0:
                    db_event_id = saved_events[0].get('id')
                
                if db_event_id:
                    # Scrape fights for this event
                    fights = scraper.scrape_fight_card(p, event['url'], "COMPLETED")
                    logger.info(f"  Scraped {len(fights)} fights.")
                    
                    for f in fights:
                        f['eventId'] = db_event_id
                            
                    fights_updated += len(fights)
                    scraper.api_client.post_fights(fights)
                else:
                    logger.warning(f"  Failed to save event {event['name']} to DB, skipping fights.")
                
                # Sleep briefly to be nice to the target server
                time.sleep(1)
                
        end_time = datetime.now()
        logger.info(f"Historical scrape completed successfully in {end_time - start_time}! Processed {len(completed_events)} events and {fights_updated} fights.")
    except Exception as e:
        logger.error(f"Historical scraper job failed: {e}", exc_info=True)

if __name__ == "__main__":
    run_historical_scrape()
