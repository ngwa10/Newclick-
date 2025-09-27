# Base image
FROM python:3.12-slim

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:1

# Install system dependencies, Chromium and Xvfb
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    xvfb \
    x11-utils \
    python3-dev \
    build-essential \
    libx11-dev \
    libxtst-dev \
    libpng-dev \
    libgl1 \
    libgl1-mesa-dri \
    wget \
    unzip \
    git \
    curl \
    fonts-liberation \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libxdamage1 \
    libxkbcommon0 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user with UID 1000
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy application files
COPY run_bot.sh core.py supervisord.conf bot.py selenium_integration.py /app/

# Fix permissions for the script
USER root
RUN chmod +x /app/run_bot.sh

# ✅ Now we can safely switch to UID 1000
USER appuser

# Copy and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Default command to start bot
CMD ["bash", "/app/run_bot.sh"]
