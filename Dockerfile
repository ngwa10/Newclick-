
# ---------- Stage 1: Build dependencies ----------
FROM python:3.12-slim AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install build tools temporarily
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Stage 2: Final runtime image ----------
FROM python:3.12-slim

# Environment variables - CRITICAL FIX
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:1
ENV PORT=8080
ENV CHROME_ARGS="--no-sandbox --disable-dev-shm-usage --disable-gpu --headless --memory-pressure-off --max_old_space_size=256 --disable-background-timer-throttling --disable-renderer-backgrounding"

# Install runtime dependencies with ChromeDriver fix
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    chromium \
    xvfb \
    x11-utils \
    x11vnc \
    git \
    tesseract-ocr \
    libx11-6 \
    libxtst6 \
    libgl1-mesa-dri \
    fonts-liberation \
    libatspi2.0-0 \
    libdbus-1-3 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxdamage1 \
    libxkbcommon0 \
    xdg-utils \
    curl \
    netcat-openbsd \
    wget \
 && apt-get clean && rm -rf /var/lib/apt/lists/* \
 && rm -rf /tmp/* /var/tmp/*

# Download ChromeDriver manually - CRITICAL FIX
RUN wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip \
 && unzip /tmp/chromedriver.zip -d /tmp/ \
 && mv /tmp/chromedriver /usr/local/bin/chromedriver \
 && chmod +x /usr/local/bin/chromedriver \
 && rm /tmp/chromedriver.zip

# Clone noVNC
RUN git clone --depth 1 https://github.com/novnc/noVNC.git /opt/noVNC \
 && git clone --depth 1 https://github.com/novnc/websockify.git /opt/noVNC/utils/websockify

# Set working directory
WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files
COPY supervisord.conf core.py bot.py wait-for-xvfb.sh health-check.sh /app/

# Fix permissions and make scripts executable
RUN chmod +x /app/wait-for-xvfb.sh /app/health-check.sh

# Use PORT environment variable - CRITICAL FIX
EXPOSE $PORT

# Health check that waits for all services
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/health-check.sh

# Start supervisord
CMD ["supervisord", "-n", "-c", "/app/supervisord.conf"]
