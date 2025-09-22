# Use Selenium standalone Chrome image
FROM selenium/standalone-chrome:114.0

# Install Python3 and pip
USER root
RUN apt-get update && apt-get install -y python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python requirements and install
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Run the bot
CMD ["python3", "bot.py"]
