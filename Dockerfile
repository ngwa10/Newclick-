# Base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    git \
    unzip \
    xvfb \
    x11-utils \
    python3-dev \
    build-essential \
    libx11-dev \
    libxtst-dev \
    libpng-dev \
    libgl1 \
    libgl1-mesa-dri \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb

# Install ChromeDriver
RUN wget -q -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/118.0.5993.90/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip \
    && chmod +x /usr/local/bin/chromedriver

# Create app directory
WORKDIR /app

# Copy application files
COPY run_bot.sh core.py supervisord.conf bot.py selenium_integration.py /app/

# Fix permissions for the script
USER root
RUN chmod +x /app/run_bot.sh
USER 1000  # Switch back to non-root user (adjust if needed)

# Copy and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Optional: Expose ports if needed
# EXPOSE 8080

# Start script
CMD ["bash", "/app/run_bot.sh"]
