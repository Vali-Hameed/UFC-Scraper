import json
import os
import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

FIGHTERS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fighters.json')

def scrape_and_update_roster(p):
    """
    Scrapes Wikipedia for the active UFC roster and updates fighters.json.
    Takes a sync_playwright instance 'p' to share the browser instance.
    """
    logger.info("Starting active roster update from Wikipedia...")
    try:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://en.wikipedia.org/wiki/List_of_current_UFC_fighters', timeout=60000)
        
        soup = BeautifulSoup(page.content(), 'html.parser')
        tables = soup.find_all('table', class_='wikitable')
        
        scraped_active = {}
        
        for t in tables:
            prev = t.find_previous(['h2', 'h3', 'h4'])
            if not prev:
                continue
                
            heading_text = prev.text.strip().lower()
            if 'weight' not in heading_text:
                continue
                
            # Clean up heading, e.g. "Heavyweights (265 lb, 120 kg)" -> "Heavyweight"
            wc_raw = prev.text.split('(')[0].strip()
            if wc_raw.lower().endswith('s'):
                wc_raw = wc_raw[:-1]
                
            # Normalize naming to match frontend (e.g. "Women's Strawweight")
            wc = wc_raw.title().replace("'S", "'s")
            if wc.startswith("Women's"):
                # Handle Women's categories explicitly if they differ
                pass
            
            names = []
            for row in t.find_all('tr')[1:]:
                cols = row.find_all(['td', 'th'])
                if len(cols) > 2:
                    name_td = cols[1]
                    link = name_td.find('a')
                    if link and not link.find('img'):
                        name = link.text.strip().replace('*', '').strip()
                    else:
                        name = name_td.text.strip().replace('*', '').strip()
                    
                    if name:
                        names.append(name)
            
            if names:
                scraped_active[wc] = names
                
        browser.close()
        
        if not scraped_active:
            logger.error("Failed to parse any weight classes from Wikipedia.")
            return False
            
        logger.info(f"Successfully scraped {sum(len(v) for v in scraped_active.values())} active fighters.")
        
        # Load existing json
        if os.path.exists(FIGHTERS_FILE):
            with open(FIGHTERS_FILE, 'r', encoding='utf-8') as f:
                roster = json.load(f)
        else:
            roster = {"Active": {}, "Inactive": {}}
            
        old_active = roster.get("Active", {})
        inactive = roster.get("Inactive", {})
        
        # Move anyone not in scraped_active to inactive
        for wc, fighters in old_active.items():
            if wc not in inactive:
                inactive[wc] = []
            
            if wc not in scraped_active and wc != "Catch Weight":
                continue
                
            for f_name in fighters:
                is_active = any(f_name in scrape_list for scrape_list in scraped_active.values())
                if not is_active:
                    if f_name not in inactive[wc]:
                        inactive[wc].append(f_name)
                        
        # Now replace the Active dictionary with the freshly scraped one
        new_active = scraped_active
        if "Catch Weight" in old_active:
            new_active["Catch Weight"] = old_active["Catch Weight"]
            
        roster["Active"] = new_active
        roster["Inactive"] = inactive
        
        # Sort fighters in each weight class
        for status in roster:
            for wc in roster[status]:
                roster[status][wc] = sorted(list(set(roster[status][wc])))
        
        # Write back
        with open(FIGHTERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(roster, f)
            
        logger.info("Successfully updated fighters.json")
        return True
        
    except Exception as e:
        logger.error(f"Error scraping active roster: {e}")
        return False
