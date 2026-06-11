<div align="center">
  <h1>🕷️ UFC Scraper Microservice</h1>
  <p><strong>Automated Python Web Scraper for Live UFC Event Data and Fighter Roster Analytics.</strong></p>
  
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=flat-square&logo=playwright&logoColor=white)
![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-000000?style=flat-square&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Oracle](https://img.shields.io/badge/Oracle_VPS-F80000?style=flat-square&logo=oracle&logoColor=white)
</div>

<hr />

## 📖 Overview

> **Note**: This repository houses the Python Scraper microservice. For the core full-stack web application, visit the [UFC-Fight-Predictor-Website](https://github.com/Vali-Hameed/UFC-Fight-Predictor-Website) repository.

This is the standalone Python microservice responsible for scraping UFC events, fight cards, results, and fighter statistics from `ufcstats.com`. It provides up-to-date data for the core UFC Fight Predictor application and the FastAPI Machine Learning model.

---

## ✨ Key Features

- **Automated Scraping**: Scheduled via cron to run nightly and before events.
- **Historical Backfilling**: Exposes an endpoint to trigger historical event scraping and resolve time-travel bugs.
- **Data Extracted**: Events, Fights, Results, and detailed Fighter Stats (matching the columns required by the ML model based on `ufc-master.csv`).
- **Secure Integration**: Authenticates with the Spring Boot backend using the `X-Scraper-Key` header.
- **Roster Management**: Retrieves structured rosters and pushes updates to the backend.

---

## 📂 Repository Structure

```text
ufc-scraper/
├── client/                   # API client for backend communication
├── scraper/                  # Core scraping logic (Playwright & BeautifulSoup)
├── main.py                   # FastAPI application entrypoint
├── scrape_historical_events.py # Script for backfilling historical events
├── fighters.json             # Cached fighter roster
├── docker-compose.yml        # Docker composition for local dev
├── Dockerfile                # Render deployment configuration
└── requirements.txt          # Python dependencies
```

---

## 🚀 Local Development Setup

### 1. Prerequisites
- Python 3.11+
- Docker & Docker Compose

### 2. Environment Configuration
Copy `.env.example` to `.env` and fill in the values:
```bash
cp .env.example .env
```
- `BACKEND_BASE_URL`: URL of the core Spring Boot API.
- `SCRAPER_API_KEY`: Secret key shared with the backend.
- `SCRAPER_CRON`: Cron expression for the APScheduler (e.g., `0 2 * * *`).

### 3. Running with Docker
```bash
docker-compose up --build
```

### 4. Running without Docker
```bash
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🔌 API Endpoints

- `GET /fighters`: Retrieves a structured JSON roster of active and inactive fighters grouped by weight class.
- `POST /trigger`: Manually starts the scraping job in the background.
- `POST /trigger/historical`: Triggers a one-off historical scraper job to backfill past events.
- `GET /health`: Health check endpoint (explicitly supports `HEAD` requests).

---

## ☁️ Deployment

This project is configured to be deployed on an **Oracle Virtual Private Server (VPS)** alongside the core UFC Fight Predictor website. 
It operates securely within a Docker Compose environment.

*(Note: While the `Dockerfile` supports dynamic `$PORT` environments for PaaS compatibility, this microservice is actively deployed on Oracle VPS.)*

---

## 🛠️ Tech Stack

### Application & APIs
- **Framework**: FastAPI (Python 3.11+)
- **Server**: Uvicorn

### Scraping
- **Static Content**: BeautifulSoup4
- **Dynamic Content**: Playwright (Chromium)

### Infrastructure
- **Deployment**: Oracle VPS
- **Containerization**: Docker
- **Scheduling**: APScheduler (Cron)

---

## 🤝 Contributing

Contributions make the open-source community an amazing place to learn, inspire, and create. Any contributions you make are greatly appreciated.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

<div align="center">
  <i>Developed by <a href="https://github.com/Vali-Hameed">Vali Hameed</a></i>
</div>
