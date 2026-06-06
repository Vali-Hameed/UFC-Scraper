import json
import os
import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

FIGHTERS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fighters.json')

import csv

def get_valid_fighters():
    valid_fighters = set()
    # Default to a local absolute path if not set, or a relative data folder if desired.
    # The default fallback aligns with the local development path.
    default_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'Documents', 'python_projects', 'UFC-Fight-Predictor', 'app', 'ufc-master.csv'))
    csv_path = os.environ.get('UFC_DATASET_PATH', default_path)
    
    if not os.path.exists(csv_path):
        logger.warning(f"Dataset not found at {csv_path}. Proceeding without dataset filtering...")
        return None # Return None to indicate no filtering
        
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'RedFighter' in row and 'BlueFighter' in row:
                    valid_fighters.add(row['RedFighter'].strip())
                    valid_fighters.add(row['BlueFighter'].strip())
        logger.info(f"Loaded {len(valid_fighters)} valid fighters from {csv_path}")
        return valid_fighters
    except Exception as e:
        logger.error(f"Error loading dataset from {csv_path}: {e}")
        return None

def format_weight_class(wc):
    # Normalize input
    wc_lower = wc.lower().replace("women's", "womens").replace(" ", "")
    
    if wc_lower == "womensbantamweight":
        return "Women's Bantamweight"
    elif wc_lower == "womensflyweight":
        return "Women's Flyweight"
    elif wc_lower == "womensstrawweight":
        return "Women's Strawweight"
    elif wc_lower == "lightheavyweight":
        return "Light Heavyweight"
    elif wc_lower == "catchweight":
        return "Catch Weight"
    else:
        return wc.title().replace("'S", "'s")

def scrape_and_update_roster(p):
    """
    Scrapes roster.watch for the active and former UFC roster and updates fighters.json.
    Takes a sync_playwright instance 'p' to share the browser instance.
    """
    logger.info("Starting active and former roster update from roster.watch...")
    try:
        valid_fighters = get_valid_fighters()
        
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Scrape Active
        logger.info("Fetching active fighters from https://roster.watch ...")
        page.goto('https://roster.watch', timeout=60000)
        active_soup = BeautifulSoup(page.content(), 'html.parser')
        
        # Scrape Former
        logger.info("Fetching former fighters from https://roster.watch/former.html ...")
        page.goto('https://roster.watch/former.html', timeout=60000)
        former_soup = BeautifulSoup(page.content(), 'html.parser')
        
        browser.close()
        
        roster = {"Active": {}, "Inactive": {}}
        
        # Helper to process soup
        def process_soup(soup, status_key):
            count = 0
            # tr with data-fighter attribute
            rows = soup.find_all('tr', attrs={'data-fighter': True})
            for row in rows:
                name = row['data-fighter'].strip()
                
                # Filter by valid fighters if a dataset exists
                if valid_fighters is not None and name not in valid_fighters:
                    continue
                    
                # Get weightclasses
                wc_data = row.get('data-weightclass_all', '[]')
                try:
                    wcs = json.loads(wc_data)
                except:
                    wcs = []
                    
                if not wcs:
                    # Fallback to single if available
                    single_wc = row.get('data-weightclass', '')
                    if single_wc:
                        wcs = [single_wc]
                    else:
                        wcs = ["Catch Weight"]
                        
                for wc in wcs:
                    formatted_wc = format_weight_class(wc)
                    if formatted_wc not in roster[status_key]:
                        roster[status_key][formatted_wc] = []
                    if name not in roster[status_key][formatted_wc]:
                        roster[status_key][formatted_wc].append(name)
                        count += 1
            return count
            
        active_count = process_soup(active_soup, "Active")
        inactive_count = process_soup(former_soup, "Inactive")
        
        if active_count == 0 and inactive_count == 0:
            logger.error("Failed to parse any fighters from roster.watch.")
            return False
            
        logger.info(f"Successfully processed {active_count} active and {inactive_count} inactive valid fighters.")
        
        # Sort fighters in each weight class
        for status in roster:
            for wc in roster[status]:
                roster[status][wc] = sorted(list(set(roster[status][wc])))
        
        # Write back
        with open(FIGHTERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(roster, f, indent=4)
            
        try:
            from client.api_client import ApiClient
            api_client = ApiClient()
            api_client.post_roster(roster)
            logger.info("Successfully pushed updated roster to the backend")
        except Exception as e:
            logger.error(f"Failed to push roster to backend: {e}")
            
        logger.info("Successfully updated fighters.json")
        return True
        
    except Exception as e:
        logger.error(f"Error scraping roster: {e}")
        return False
