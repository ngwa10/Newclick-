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

# Copy only requirements first to leverage Docker cache.
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt


# ---------- Stage 2: Final runtime image ----------
FROM python:3.12-slim

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:1
ENV PORT=6080
ENV CHROME_ARGS="--no-sandbox --disable-dev-shm-usage --disable-gpu --headless --memory-pressure-off --max_old_space_size=2048 --disable-background-timer-throttling --disable-renderer-backgrounding"

# Install runtime dependencies - optimized for smaller size and better performance
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    chromium \
    chromium-driver \
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
 && apt-get clean && rm -rf /var/lib/apt/lists/* \
 && rm -rf /tmp/* /var/tmp/*

RUN pip install numpy

# Clone noVNC and websockify - keep git as noVNC needs it for websockify
RUN git clone --depth 1 https://github.com/novnc/noVNC.git /opt/noVNC \
 && git clone --depth 1 https://github.com/novnc/websockify.git /opt/noVNC/utils/websockify

# Set working directory
WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files
COPY run_bot.sh core.py supervisord.conf bot.py selenium_integration.py wait-for-xvfb.sh health-check.sh /app/

# Fix permissions and make scripts executable
RUN chmod +x /app/run_bot.sh /app/wait-for-xvfb.sh /app/health-check.sh

# Expose the port for noVNC (this should match your Zeabur port setting)
EXPOSE 6080

# Robust health check that waits for all services
HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=5 \
    CMD /app/health-check.sh

# Start supervisord in foreground
CMD ["supervisord", "-n", "-c", "/app/supervisord.conf"]
