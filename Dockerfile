FROM python:3.12-slim-bookworm

# Set working directory
WORKDIR /app

# --- Install system dependencies (for pip, sqlite, etc.) ---
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       sqlite3 \
       curl \
       git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# --- Set environment variables ---
ENV PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:${PATH}"

# --- Install Python dependencies ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copy project files ---
COPY . .

# Default command (overridable in docker-compose)
CMD ["python", "scraper.py"]
