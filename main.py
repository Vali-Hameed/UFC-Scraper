from fastapi import FastAPI, BackgroundTasks, HTTPException
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import os
from dotenv import load_dotenv

from scraper.ufc_stats_scraper import run_scraper_job

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="UFC Scraper Microservice")

scheduler = BackgroundScheduler()

@app.on_event("startup")
def startup_event():
    cron_expr = os.getenv("SCRAPER_CRON", "0 2 * * *")
    logger.info(f"Starting scheduler with cron: {cron_expr}")
    try:
        minute, hour, day, month, day_of_week = cron_expr.split()
        scheduler.add_job(
            run_scraper_job,
            CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week),
            id="daily_scraper"
        )
        scheduler.start()
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

@app.get("/fighters")
def get_fighters():
    """Return the active and inactive fighters roster."""
    import json
    file_path = os.path.join(os.path.dirname(__file__), 'fighters.json')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"Active": {}, "Inactive": {}}

@app.post("/trigger")
def trigger_scrape(background_tasks: BackgroundTasks):
    """Manually trigger the scraper job."""
    background_tasks.add_task(run_scraper_job)
    return {"message": "Scraper job triggered in the background"}

@app.post("/trigger/historical")
def trigger_historical_scrape(background_tasks: BackgroundTasks):
    """Manually trigger a one-off historical scraper job."""
    from scraper.ufc_stats_scraper import run_historical_scraper_job
    background_tasks.add_task(run_historical_scraper_job)
    return {"message": "Historical scraper job triggered in the background"}

@app.get("/health")
@app.head("/health")
def health_check():
    return {"status": "ok"}
