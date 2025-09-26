# 🐍 Use a lightweight Python base image
FROM python:3.10-slim

# 📁 Set working directory inside the container
WORKDIR /app

# 📦 Install system dependencies (for Selenium + Chrome)
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    xvfb \
    x11vnc \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# 🌐 Install Chrome
RUN curl -SL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o chrome.deb \
    && apt install -y ./chrome.deb \
    && rm chrome.deb

# 🧠 Install ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d '.' -f 1) \
    && DRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION") \
    && curl -SL "https://chromedriver.storage.googleapis.com/${DRIVER_VERSION}/chromedriver_linux64.zip" -o chromedriver.zip \
    && unzip chromedriver.zip \
    && mv chromedriver /usr/bin/chromedriver \
    && chmod +x /usr/bin/chromedriver \
    && rm chromedriver.zip

# 📥 Copy all files into the container
COPY . /app

# 📚 Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 🔧 Expose noVNC port
EXPOSE 6080

# 🚀 Start everything using supervisord
CMD ["supervisord", "-c", "/app/supervisord.conf"]
