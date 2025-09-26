# -----------------------
# Base image
# -----------------------
FROM python:3.11-slim

# -----------------------
# Install system dependencies
# -----------------------
RUN apt-get update && apt-get install -y \
    wget gnupg unzip curl x11vnc xvfb net-tools git python3-pip \
    supervisor fonts-liberation libappindicator3-1 \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 \
    libdbus-1-3 libgdk-pixbuf-2.0-0 libnspr4 libnss3 \
    libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
    xdg-utils libgl1 libxrender1 libxext6 \
    libgtk-3-0 python3-tk scrot wmctrl \
    netcat \
    && rm -rf /var/lib/apt/lists/*

# -----------------------
# Install Google Chrome
# -----------------------
RUN wget -q -O /usr/share/keyrings/google-linux-signing-key.gpg https://dl.google.com/linux/linux_signing_key.pub \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-key.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
       > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable

# -----------------------
# Install ChromeDriver
# -----------------------
RUN CHROME_VERSION=$(google-chrome --version | grep -oE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+") && \
    MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d. -f1) && \
    DRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_$MAJOR_VERSION") && \
    wget -q "https://storage.googleapis.com/chrome-for-testing-public/$DRIVER_VERSION/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip && \
    unzip /tmp/chromedriver.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/*

# -----------------------
# Install noVNC
# -----------------------
RUN git clone https://github.com/novnc/noVNC.git /opt/noVNC \
    && git clone https://github.com/novnc/websockify /opt/noVNC/utils/websockify \
    && chmod +x /opt/noVNC/utils/novnc_proxy

# -----------------------
# Copy app and install Python dependencies
# -----------------------
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Make all scripts executable
RUN chmod +x /app/run_bot.sh \
            /app/wait_for_vnc.sh \
            /app/wait_for_vnc_then_bot.sh

# -----------------------
# Ensure Xauthority exists
# -----------------------
RUN touch /tmp/.Xauthority && chmod 600 /tmp/.Xauthority

# -----------------------
# Increase /dev/shm for Chrome
# -----------------------
VOLUME /dev/shm

# -----------------------
# Expose VNC and noVNC ports
# -----------------------
EXPOSE 5900 6080

# -----------------------
# Start supervisord
# -----------------------
CMD ["/bin/bash", "-c", "/usr/bin/supervisord -c /app/supervisord.conf"]
