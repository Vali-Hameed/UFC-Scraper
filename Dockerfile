FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Use shell form for CMD so we can access the Render $PORT variable, defaulting to 8000 locally
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
