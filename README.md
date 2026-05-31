![UFC Logo](https://upload.wikimedia.org/wikipedia/commons/9/92/UFC_Logo.svg)

# UFC Scraper Microservice

This is the standalone Python microservice responsible for scraping UFC events, fight cards, results, and fighter statistics from `ufcstats.com`. It provides up-to-date data for the core UFC Fight Predictor application and the FastAPI Machine Learning model.

## Features
- **Automated Scraping:** Scheduled via cron to run nightly and before events.
- **Data Extracted:** Events, Fights, Results, and detailed Fighter Stats (matching the columns required by the ML model based on `ufc-master.csv`).
- **Secure Integration:** Authenticates with the Spring Boot backend using the `X-Scraper-Key` header.
- **Manual Trigger:** Exposes a FastAPI endpoint (`POST /trigger`) to initiate scraping on demand.

## Requirements
- Python 3.11+
- Docker & Docker Compose

## Environment Variables
Copy `.env.example` to `.env` and fill in the values:
```bash
cp .env.example .env
```
- `BACKEND_BASE_URL`: URL of the core Spring Boot API.
- `SCRAPER_API_KEY`: Secret key shared with the backend.
- `SCRAPER_CRON`: Cron expression for the APScheduler (e.g., `0 2 * * *`).

## Running Locally

### With Docker
```bash
docker-compose up --build
```

### Without Docker
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints
- `POST /trigger`: Manually starts the scraping job in the background.
- `GET /health`: Health check endpoint.
