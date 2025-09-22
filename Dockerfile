# Use Selenium Chrome standalone with VNC
FROM selenium/standalone-chrome:114.0

# Set working directory
WORKDIR /app

# Copy bot files
COPY requirements.txt .
COPY bot.py .

# Install Python dependencies
USER root
RUN apt-get update && \
    apt-get install -y python3-pip python3-dotenv && \
    pip3 install --no-cache-dir -r requirements.txt

# Set user back to seluser (default for selenium/standalone-chrome)
USER seluser

# Run bot
CMD ["python3", "/app/bot.py"]
