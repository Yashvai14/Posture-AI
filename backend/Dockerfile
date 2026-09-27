FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies for OpenCV, MediaPipe, Pillow, Psycopg, and ReportLab
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgl1 \
    libegl1 \
    libgles2 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure storage, uploads, and model folders exist
RUN mkdir -p /app/storage /app/uploads

EXPOSE 8000

# Wait for DB to be reachable, apply Alembic migrations, then launch Uvicorn
CMD ["sh", "-c", "python -c \"import time, os, psycopg; url = os.environ.get('DATABASE_URL',''); print('Checking database connection...'); [time.sleep(1) for _ in range(30) if psycopg.connect(url, connect_timeout=2) is None]\" 2>/dev/null || true; alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
