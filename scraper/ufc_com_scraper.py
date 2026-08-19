import requests
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

def scrape_ufc_com_event_tiers(url: str) -> dict:
    """Scrape a specific UFC.com event URL for tiers"""
    tiers = {}
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        for card_id, tier_name in [('#main-card', 'Main Card'), ('#prelims-card', 'Prelims'), ('#early-prelims', 'Early Prelims')]:
            card_section = soup.select_one(card_id)
            if card_section:
                fights = card_section.select('.c-listing-fight')
                for f in fights:
                    names = f.select('.c-listing-fight__corner-name')
                    for n in names:
                        # Clean up name
                        # UFC.com formats as GivenName FamilyName
                        given = n.select_one('.c-listing-fight__corner-given-name')
                        family = n.select_one('.c-listing-fight__corner-family-name')
                        if given and family:
                            full_name = f"{given.text.strip()} {family.text.strip()}".lower()
                            tiers[full_name] = tier_name
    except Exception as e:
        logger.warning(f"Error scraping UFC.com event: {e}")
    return tiers

def get_all_ufc_com_tiers() -> dict:
    """Gets tiers for the most recent/upcoming events on the main page."""
    tiers = {}
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get('https://www.ufc.com/events', headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        event_links = soup.select('.c-card-event--result__logo a')
        for link in event_links[:10]: # Check top 10 events to ensure we cover everything the main scraper checks
            url = 'https://www.ufc.com' + link['href']
            event_tiers = scrape_ufc_com_event_tiers(url)
            tiers.update(event_tiers)
    except Exception as e:
        logger.warning(f"Failed to fetch UFC.com events list: {e}")
    return tiers
