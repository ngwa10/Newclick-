# 🐍 Base image
FROM python:3.11-slim

# 🛠️ Set noninteractive mode to avoid debconf errors
ENV DEBIAN_FRONTEND=noninteractive

# 🚫 Prevent services from starting during build
RUN echo 'exit 101' > /usr/sbin/policy-rc.d && chmod +x /usr/sbin/policy-rc.d

# 📦 Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg unzip curl x11vnc xvfb net-tools git python3-pip \
    supervisor fonts-liberation libappindicator3-1 \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 \
    libdbus-1-3 libgdk-pixbuf-2.0-0 libnspr4 libnss3 \
    libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
    libgl1 libxrender1 libxext6 libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

# 🧩 Install patched xdg-utils to fix Chrome dependency issues
RUN wget https://raw.githubusercontent.com/LASR-UCI/xdg-utils/master/xdg-utils_1.1.3_rc1-2_all.deb \
    && dpkg -i xdg-utils_1.1.3_rc1-2_all.deb \
    && rm xdg-utils_1.1.3_rc1-2_all.deb

# 🌐 Install Google Chrome
RUN curl -SL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o chrome.deb \
    && apt-get update && apt-get install -y ./chrome.deb \
    && rm chrome.deb

# 🧭 Install ChromeDriver
RUN DRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE") \
    && wget -q "https://chromedriver.storage.googleapis.com/${DRIVER_VERSION}/chromedriver_linux64.zip" -O /tmp/chromedriver.zip \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/*

# 🖥️ Install noVNC
RUN git clone https://github.com/novnc/noVNC.git /opt/noVNC \
    && git clone https://github.com/novnc/websockify /opt/noVNC/utils/websockify \
    && ln -s /opt/noVNC /usr/share/novnc

# 📁 Copy app files
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# 🌐 Expose VNC and noVNC ports
EXPOSE 5900 6080

# 🚀 Start everything with supervisord
CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]
