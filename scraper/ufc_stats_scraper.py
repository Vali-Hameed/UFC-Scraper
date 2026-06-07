import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from datetime import datetime
from typing import List, Dict, Any
import time
import requests

from client.api_client import ApiClient

logger = logging.getLogger(__name__)

class UFCStatsScraper:
    def __init__(self):
        self.completed_url = "http://ufcstats.com/statistics/events/completed?page=all"
        self.upcoming_url = "http://ufcstats.com/statistics/events/upcoming?page=all"
        self.api_client = ApiClient()
        self.api_client = ApiClient()

    def scrape_events(self, p, url: str, default_status: str) -> List[Dict[str, Any]]:
        """Scrape the events page."""
        logger.info(f"Scraping events list from {url}...")
        
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        
        # Wait for the anti-bot check to clear and the main table to appear
        page.wait_for_selector('.b-statistics__table-events', timeout=30000)
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        events_data = []
        rows = soup.select('.b-statistics__table-events tr.b-statistics__table-row')
        
        # Skip the header row (index 0) and the first row which is upcoming event
        for row in rows[1:]:
            columns = row.select('td')
            if not columns:
                continue
            
            link_tag = columns[0].select_one('a')
            if not link_tag:
                continue
                
            name = link_tag.text.strip()
            event_url = link_tag['href']
            
            date_tag = columns[0].select_one('.b-statistics__date')
            date_str = date_tag.text.strip() if date_tag else None
            
            location = columns[1].text.strip().replace('\n', ' ') if len(columns) > 1 else None
            
            status = default_status
            iso_date_str = None
            if date_str:
                try:
                    event_date = datetime.strptime(date_str, "%B %d, %Y")
                    # Add UTC timezone info for ISO-8601 compatibility with OffsetDateTime
                    iso_date_str = event_date.isoformat() + "Z"
                except Exception:
                    pass
            
            events_data.append({
                "name": name,
                "eventDate": iso_date_str,
                "location": location,
                "url": event_url,
                "status": status
            })
            
        browser.close()
        return events_data

    def scrape_fight_card(self, p, event_url: str, event_status: str = "COMPLETED") -> List[Dict[str, Any]]:
        """Scrape the fights for a specific event URL."""
        logger.info(f"Scraping fight card from {event_url}...")
        
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(event_url)
        page.wait_for_selector('.b-fight-details__table', timeout=30000)
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        fights_data = []
        
        for idx, row in enumerate(soup.select('tbody tr')):
            cols = row.select('td')
            if not cols or len(cols) < 2:
                continue
                
            fighters = cols[1].select('a')
            if len(fighters) < 2:
                continue
                
            fighter1_name = fighters[0].text.strip()
            fighter2_name = fighters[1].text.strip()
            fighter1_url = fighters[0]['href']
            fighter2_url = fighters[1]['href']
            
            weight_class = cols[6].text.strip() if len(cols) > 6 else None
            
            # Additional details like method, round, time for COMPLETED fights
            method = cols[7].select_one('p').text.strip() if len(cols) > 7 and cols[7].select_one('p') else None
            win_round = cols[8].select_one('p').text.strip() if len(cols) > 8 and cols[8].select_one('p') else None
            time = cols[9].select_one('p').text.strip() if len(cols) > 9 and cols[9].select_one('p') else None
            
            winner = None
            is_draw = False
            is_nc = False
            br_found = False
            for child in cols[0].children:
                if child.name == 'br':
                    br_found = True
                    continue
                
                if child.name:
                    badge_text = child.text.strip().lower()
                    if "win" in badge_text:
                        if not br_found:
                            winner = fighter1_name
                        else:
                            winner = fighter2_name
                        break
                    elif "draw" in badge_text:
                        is_draw = True
                        break
                    elif "nc" in badge_text:
                        is_nc = True
                        break
                        
            if is_draw:
                winner = "Draw"
            elif is_nc:
                winner = "No Contest"
                    
            fight_status = event_status
            if event_status == "COMPLETED" and not winner:
                fight_status = "CANCELED"
                winner = "Canceled"
            elif event_status == "UPCOMING":
                fight_status = "UPCOMING"
            
            fights_data.append({
                "fighter1Name": fighter1_name,
                "fighter2Name": fighter2_name,
                "weightClass": weight_class,
                "isMainEvent": idx == 0,
                "fightOrder": idx,
                "resultWinner": winner,
                "resultMethod": method,
                "resultRound": win_round,
                "resultTime": time,
                "fighter1Url": fighter1_url,
                "fighter2Url": fighter2_url,
                "status": fight_status
            })
            
        browser.close()
        return fights_data

    def scrape_fighter_stats(self, p, fighter_url: str) -> Dict[str, Any]:
        """Scrape detailed fighter stats to match the ML model ufc-master.csv format."""
        logger.info(f"Scraping fighter stats from {fighter_url}...")
        
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(fighter_url)
        page.wait_for_selector('.b-list__info-box-left', timeout=30000)
        
        soup = BeautifulSoup(page.content(), 'html.parser')
        
        stats = {
            "name": soup.select_one('.b-content__title-highlight').text.strip() if soup.select_one('.b-content__title-highlight') else "Unknown",
            "Wins": 0, "Losses": 0, "Draws": 0,
            "WinsByKO": 0, "WinsBySubmission": 0, "WinsByDecision": 0,
            "CurrentWinStreak": 0, "CurrentLoseStreak": 0, "LongestWinStreak": 0,
            "TotalRoundsFought": 0
        }
        
        # Physical stats and Career averages
        info_items = soup.select('.b-list__box-list-item')
        for item in info_items:
            text = item.text.strip().replace('  ', '').replace('\n', '')
            if "Height:" in text:
                stats['Height'] = text.replace("Height:", "").strip()
            elif "Weight:" in text:
                stats['Weight'] = text.replace("Weight:", "").strip()
            elif "Reach:" in text:
                stats['Reach'] = text.replace("Reach:", "").strip()
            elif "STANCE:" in text:
                stats['Stance'] = text.replace("STANCE:", "").strip()
            elif "DOB:" in text:
                stats['DOB'] = text.replace("DOB:", "").strip()
            elif "SLpM:" in text:
                stats['AvgSigStrLanded'] = text.replace("SLpM:", "").strip()
            elif "Str. Acc.:" in text:
                stats['AvgSigStrPct'] = text.replace("Str. Acc.:", "").replace("%", "").strip()
            elif "SApM:" in text:
                stats['SApM'] = text.replace("SApM:", "").strip()
            elif "Str. Def:" in text:
                stats['StrDef'] = text.replace("Str. Def:", "").replace("%", "").strip()
            elif "TD Avg.:" in text:
                stats['AvgTDLanded'] = text.replace("TD Avg.:", "").strip()
            elif "TD Acc.:" in text:
                stats['AvgTDPct'] = text.replace("TD Acc.:", "").replace("%", "").strip()
            elif "TD Def.:" in text:
                stats['TDDef'] = text.replace("TD Def.:", "").replace("%", "").strip()
            elif "Sub. Avg.:" in text:
                stats['AvgSubAtt'] = text.replace("Sub. Avg.:", "").strip()
                
        # Fight History Parsing (for streaks, method of wins, rounds fought)
        history_rows = soup.select('.b-fight-details__table-row.b-fight-details__table-row__hover.js-fight-details-click')
        
        current_win_streak = 0
        current_lose_streak = 0
        streak_broken = False
        longest_win_streak = 0
        temp_win_streak = 0
        
        for row in history_rows:
            cols = row.select('td')
            if not cols or len(cols) < 10:
                continue
                
            # Result: win/loss/draw/nc
            result_flag = cols[0].select_one('.b-flag__text')
            result = result_flag.text.strip().lower() if result_flag else ""
            
            # Method of victory (KO/TKO, SUB, DEC)
            method_p = cols[7].select_one('p')
            method = method_p.text.strip().lower() if method_p else ""
            
            # Rounds fought in this match
            rnd_p = cols[8].select_one('p')
            if rnd_p and rnd_p.text.strip().isdigit():
                stats["TotalRoundsFought"] += int(rnd_p.text.strip())
                
            if result == 'win':
                stats['Wins'] += 1
                temp_win_streak += 1
                if temp_win_streak > longest_win_streak:
                    longest_win_streak = temp_win_streak
                
                if not streak_broken:
                    current_win_streak += 1
                else:
                    streak_broken = True
                    
                if "ko" in method or "tko" in method:
                    stats['WinsByKO'] += 1
                elif "sub" in method:
                    stats['WinsBySubmission'] += 1
                elif "dec" in method:
                    stats['WinsByDecision'] += 1
                    
            elif result == 'loss':
                stats['Losses'] += 1
                temp_win_streak = 0
                if not streak_broken:
                    current_lose_streak += 1
                    streak_broken = True
            elif result == 'draw':
                stats['Draws'] += 1
                temp_win_streak = 0
                streak_broken = True
                
        stats['CurrentWinStreak'] = current_win_streak
        stats['CurrentLoseStreak'] = current_lose_streak
        stats['LongestWinStreak'] = longest_win_streak
                
        browser.close()
        return stats

def run_scraper_job():
    """Main execution function for the scheduled cron job."""
    logger.info("Starting scheduled UFC scraper job...")
    start_time = datetime.now()
    
    scraper = UFCStatsScraper()
    
    try:
        with sync_playwright() as p:
            # 1. Scrape Events
            upcoming_events = scraper.scrape_events(p, scraper.upcoming_url, "UPCOMING")
            completed_events = scraper.scrape_events(p, scraper.completed_url, "COMPLETED")
            
            # Process the top 6 events (Upcoming + 1 Completed)            
            events_to_process = upcoming_events[:5] + completed_events[:1]
            logger.info(f"Scraped {len(upcoming_events) + len(completed_events)} total events. Processing {len(events_to_process)} events.")
            
            # --- ESPN Exact Time Merge ---
            try:
                r = requests.get('https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard', timeout=10)
                if r.status_code == 200:
                    espn_events = r.json().get('events', [])
                    for espn_ev in espn_events:
                        espn_exact_date = espn_ev.get('date') # e.g. "2026-06-06T21:00Z"
                        if espn_exact_date:
                            espn_day = espn_exact_date[:10]
                            # match with events_to_process
                            for ev in events_to_process:
                                if ev.get('eventDate') and ev['eventDate'][:10] == espn_day:
                                    logger.info(f"Matched ESPN exact time for event {ev['name']}: {espn_exact_date}")
                                    ev['eventDate'] = espn_exact_date
            except Exception as e:
                logger.warning(f"Failed to fetch exact time from ESPN API: {e}")
            # ------------------------------
            
            fights_updated = 0
            for recent_event in events_to_process:
                # post_events returns the saved entities from the backend
                saved_events = scraper.api_client.post_events([recent_event])
                db_event_id = None
                if saved_events and isinstance(saved_events, list) and len(saved_events) > 0:
                    db_event_id = saved_events[0].get('id')
                
                # 2. Scrape fight card for the event
                fights = scraper.scrape_fight_card(p, recent_event['url'], recent_event['status'])
                logger.info(f"Scraped {len(fights)} fights for {recent_event['name']}")
                
                if db_event_id:
                    for f in fights:
                        f['eventId'] = db_event_id
                
                fights_updated += len(fights)
                scraper.api_client.post_fights(fights)
                
                # 3. For ML completeness, scrape the fighters in the first fight
                if fights:
                    first_fight = fights[0]
                    f1_stats = scraper.scrape_fighter_stats(p, first_fight['fighter1Url'])
                    f2_stats = scraper.scrape_fighter_stats(p, first_fight['fighter2Url'])
                    logger.info(f"Fighter 1 Stats: {f1_stats}")
                    logger.info(f"Fighter 2 Stats: {f2_stats}")
            
            # --- 4. Update the Active Fighter Roster ---
            from scraper.roster_scraper import scrape_and_update_roster
            scrape_and_update_roster(p)
            # -------------------------------------------
        
        end_time = datetime.now()
        logger.info(f"Scraper job completed successfully in {end_time - start_time}")
        scraper.api_client.post_logs({
            "startedAt": start_time.isoformat() + "Z",
            "completedAt": end_time.isoformat() + "Z",
            "eventsFound": len(events_to_process) if 'events_to_process' in locals() else 0,
            "fightsUpdated": fights_updated,
            "status": "COMPLETED",
            "errorMessage": None
        })
        
    except Exception as e:
        logger.error(f"Scraper job failed: {e}", exc_info=True)
        end_time = datetime.now()
        scraper.api_client.post_logs({
            "startedAt": start_time.isoformat() + "Z",
            "completedAt": end_time.isoformat() + "Z",
            "eventsFound": 0,
            "fightsUpdated": 0,
            "status": "FAILED",
            "errorMessage": str(e)
        })

def run_historical_scraper_job():
    """Main execution function for a one-off historical scrape."""
    logger.info("Starting historical UFC scraper job...")
    start_time = datetime.now()
    
    scraper = UFCStatsScraper()
    
    try:
        with sync_playwright() as p:
            completed_events = scraper.scrape_events(p, scraper.completed_url, "COMPLETED")
            logger.info(f"Scraped {len(completed_events)} historical events.")
            
            fights_updated = 0
            
            for idx, event in enumerate(completed_events):
                logger.info(f"Processing event {idx + 1}/{len(completed_events)}: {event['name']}")
                
                saved_events = scraper.api_client.post_events([event])
                db_event_id = None
                if saved_events and isinstance(saved_events, list) and len(saved_events) > 0:
                    db_event_id = saved_events[0].get('id')
                
                if db_event_id:
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
