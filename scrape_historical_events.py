import logging
from playwright.sync_api import sync_playwright
from datetime import datetime
import time
import requests
import re
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
            
            # --- START ESPN TIME SYNC ---
            logger.info("Fetching precise historical event times from ESPN...")
            current_year = datetime.now().year
            espn_events = []
            for year in range(1993, current_year + 1):
                url = f'https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard?dates={year}'
                try:
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        espn_events.extend(r.json().get('events', []))
                except Exception as e:
                    logger.error(f"Failed to fetch ESPN events for {year}: {e}")
                    
            logger.info(f"Fetched {len(espn_events)} total events from ESPN history.")
            
            updates_count = 0
            for espn_ev in espn_events:
                espn_exact_date = espn_ev.get('date')
                espn_name = espn_ev.get('name', '').lower().replace(':', '').replace('-', ' ')
                if not espn_exact_date: continue
                
                try:
                    parsed_espn_time = datetime.strptime(espn_exact_date, "%Y-%m-%dT%H:%MZ")
                    espn_exact_date = parsed_espn_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    pass
                espn_date_obj = datetime.strptime(espn_exact_date[:10], "%Y-%m-%d")
                
                espn_num = re.search(r'\b(\d{3})\b', espn_name)
                espn_words = set(w for w in espn_name.split() if len(w) >= 3 and w not in ['fight', 'night', 'edition', 'live', 'road', 'ufc', 'freedom'])
                
                for ev in completed_events:
                    if ev.get('eventDate'):
                        ev_date_obj = datetime.strptime(ev['eventDate'][:10], "%Y-%m-%d")
                        if abs((espn_date_obj - ev_date_obj).days) <= 2:
                            ev_name = ev.get('name', '').lower().replace(':', '').replace('-', ' ')
                            ev_num = re.search(r'\b(\d{3})\b', ev_name)
                            ev_words = set(w for w in ev_name.split() if len(w) >= 3 and w not in ['fight', 'night', 'edition', 'live', 'road', 'ufc', 'freedom'])
                            
                            is_match = False
                            if ev_num and espn_num:
                                if ev_num.group(1) == espn_num.group(1):
                                    is_match = True
                            elif ev_words.intersection(espn_words):
                                is_match = True
                                
                            if is_match:
                                if ev['eventDate'] != espn_exact_date:
                                    ev['eventDate'] = espn_exact_date
                                    updates_count += 1
                                break
            
            logger.info(f"Successfully merged exact ESPN start times into {updates_count} historical events.")
            # --- END ESPN TIME SYNC ---
            
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
