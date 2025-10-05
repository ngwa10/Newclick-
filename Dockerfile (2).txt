FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:1 \
    VNC_RESOLUTION=1280x800 \
    NO_VNC_HOME=/opt/noVNC

# -------------------------
# Install packages
# -------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget ca-certificates gnupg2 \
    python3 python3-pip git unzip \
    tigervnc-standalone-server tigervnc-tools \
    xfce4-session xfce4-panel xfce4-terminal dbus-x11 procps dos2unix \
    python3-tk python3-dev scrot xclip xsel \
    && rm -rf /var/lib/apt/lists/*

# -------------------------
# Install Chrome
# -------------------------
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# -------------------------
# ChromeDriver
# -------------------------
RUN CHROME_VERSION=$(google-chrome --version | sed 's/[^0-9.]//g' | cut -d. -f1) \
    && LATEST_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_VERSION}") \
    && wget -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${LATEST_URL}/linux64/chromedriver-linux64.zip" \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver.zip /usr/local/bin/chromedriver-linux64

# -------------------------
# Install Python packages
# -------------------------
RUN pip3 install --no-cache-dir pytz selenium telethon numpy python-dotenv pyautogui pillow

# -------------------------
# Install noVNC
# -------------------------
RUN git clone --depth 1 --branch v1.4.0 https://github.com/novnc/noVNC.git ${NO_VNC_HOME} \
    && git clone --depth 1 https://github.com/novnc/websockify.git ${NO_VNC_HOME}/utils/websockify \
    && chmod +x ${NO_VNC_HOME}/utils/websockify/run

# -------------------------
# Copy start.sh and convert (as root)
# -------------------------
COPY start.sh /usr/local/bin/start.sh
RUN dos2unix /usr/local/bin/start.sh && chmod +x /usr/local/bin/start.sh

# -------------------------
# Create non-root user
# -------------------------
RUN useradd -m -s /bin/bash -u 1000 dockuser \
    && mkdir -p /home/dockuser/.vnc /home/dockuser/chrome-profile

# -------------------------
# Copy bot files (change ownership)
# -------------------------
COPY .env core.py selenium_integration.py telegram_listener.py telegram_callbacks.py core_utils.py logs.json /home/dockuser/
RUN chown -R dockuser:dockuser /home/dockuser

USER dockuser
WORKDIR /home/dockuser

EXPOSE 5901 6080

ENTRYPOINT ["/usr/local/bin/start.sh"]
