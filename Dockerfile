# Use Selenium standalone Chrome image (includes Chrome + Chromedriver)
FROM selenium/standalone-chrome:114.0

# Set working directory
WORKDIR /app

# Copy Python requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Run the bot
CMD ["python", "bot.py"]
