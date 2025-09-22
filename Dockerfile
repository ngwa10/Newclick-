# Base image
FROM python:3.11-slim

# Install dependencies + Chrome + Xvfb + noVNC
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    x11vnc \
    xvfb \
    net-tools \
    novnc \
    websockify \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf-2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libgl1 \
    libxrender1 \
    libxext6 \
    && wget -q -O /usr/share/keyrings/google-linux-signing-key.gpg https://dl.google.com/linux/linux_signing_key.pub \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-key.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Expose noVNC port
EXPOSE 5901 6080

# Start Xvfb and noVNC, then run bot
CMD Xvfb :1 -screen 0 1920x1080x24 & \
    x11vnc -display :1 -nopw -forever -shared & \
    websockify -D --web=/usr/share/novnc/ 6080 localhost:5901 & \
    export DISPLAY=:1 && python bot.py
    
