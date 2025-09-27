# ---------- Stage 1: Build dependencies ----------
FROM python:3.12-bookworm-slim AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set workdir
WORKDIR /app

# Install build tools (temporary)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Stage 2: Final runtime image ----------
FROM python:3.12-bookworm-slim

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:1

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    chromium \
    chromium-driver \
    xvfb \
    x11-utils \
    libx11-6 \
    libxtst6 \
    libpng16-16 \
    libgl1 \
    libgl1-mesa-dri \
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
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy your application files
COPY run_bot.sh core.py supervisord.conf bot.py selenium_integration.py /app/

# Fix permissions
RUN chmod +x /app/run_bot.sh && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Start everything via supervisord
CMD ["supervisord", "-c", "/app/supervisord.conf"]
