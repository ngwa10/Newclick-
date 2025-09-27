"""
Core logic for Pocket Option Telegram Trading Bot.
Includes: main bot orchestrator, trade manager, Telegram listener, health server, and WebDriver setup.
"""

import os
import sys
import time
import threading
import logging
import signal
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any

# =========================
# HARD-CODED CREDENTIALS
# =========================
# Pocket Option credentials
EMAIL = "mylivemyfuture@123gmail.com"
PASSWORD = "AaCcWw3468,"

# Telegram credentials
TELEGRAM_API_ID = 29630724
TELEGRAM_API_HASH = "8e12421a95fd722246e0c0b194fd3e0c"
TELEGRAM_BOT_TOKEN = "8477806088:AAGEXpIAwN5tNQM0hsCGqP-otpLJjPJLmWA"
TELEGRAM_CHANNEL = "-1003033183667"

# Health server port (bot internal)
WEB_PORT = 8080

# noVNC UI port
PORT = 6080

# POST_LOGIN_WAIT seconds for manual login / CAPTCHA
POST_LOGIN_WAIT = 180

# =========================
# Logging Setup
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/bot.log')
    ]
)
logger = logging.getLogger(__name__)

# =========================
# Health Check Server
# =========================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/health', '/', '/status']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = '{"status": "healthy", "bot": "running", "timestamp": "' + str(time.time()) + '"}'
            self.wfile.write(response.encode())
        elif self.path == '/vnc.html':
            self.send_response(302)
            self.send_header('Location', '/vnc_lite.html')
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, format, *args):
        pass  # suppress logs

def start_health_server():
    """Start health check server"""
    try:
        logger.info(f"Starting health server on port {PORT}")
        server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
        server.serve_forever()
    except Exception as e:
        logger.error(f"Health server failed to start: {e}")

# =========================
# Optional GUI / OCR libs
# =========================
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
    logger.info("pyautogui loaded successfully")
except Exception:
    pyautogui = None
    logger.warning("pyautogui not available")

try:
    import pytesseract
    logger.info("pytesseract loaded successfully")
except Exception:
    pytesseract = None
    logger.warning("pytesseract not available")

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import WebDriverException
    logger.info("Selenium imports successful")
except Exception as e:
    logger.error(f"Selenium import failed: {e}")
    sys.exit(1)

# =========================
# Display / Xvfb Setup
# =========================
os.environ.setdefault('DISPLAY', ':1')
os.environ.setdefault('XAUTHORITY', '/tmp/.Xauthority')
if not os.path.exists('/tmp/.Xauthority'):
    open('/tmp/.Xauthority', 'a').close()
    logger.info("[✅] Created /tmp/.Xauthority file")

# =========================
# Telegram integration
# =========================
try:
    from telegram_integration import start_telegram_listener, parse_signal
    logger.info("Telegram integration module loaded")
except Exception as e:
    start_telegram_listener = None
    parse_signal = None
    logger.warning(f"Telegram listener not available: {e}")

# =========================
# WebDriver Setup
# =========================
def setup_driver(chromedriver_path: str = "/usr/bin/chromedriver", headless: bool = False,
                 user_data_dir: str = "/tmp/chrome-user-data") -> Optional[webdriver.Chrome]:
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument("--window-size=1280,720")
    chrome_options.add_argument(f"--display={os.environ.get('DISPLAY', ':1')}")
    chrome_options.add_argument("--remote-debugging-port=9222")
    if headless:
        chrome_options.add_argument("--headless=new")
    
    service = Service(chromedriver_path)
    for attempt in range(3):
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get("https://pocketoption.com/en/login/")
            logger.info("[✅] Chrome started and navigated to login page")
            
            # Autofill credentials if available
            try:
                email_input = driver.find_element(By.NAME, "email")
                password_input = driver.find_element(By.NAME, "password")
                email_input.clear()
                email_input.send_keys(EMAIL)
                password_input.clear()
                password_input.send_keys(PASSWORD)
                logger.info(f"[🚨] Credentials entered. Waiting {POST_LOGIN_WAIT}s for manual login / CAPTCHA")
                time.sleep(POST_LOGIN_WAIT)
            except Exception:
                pass
            return driver
        except WebDriverException as e:
            logger.warning(f"WebDriver attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(5)
    logger.error("All WebDriver setup attempts failed")
    return None

# =========================
# Trade Manager
# =========================
class TradeManager:
    def __init__(self, driver: Optional[webdriver.Chrome] = None, base_amount: float = 1.0, max_martingale: int = 2):
        self.trading_active = False
        self.driver = driver
        self.base_amount = base_amount
        self.max_martingale = max_martingale
    
    def wait_until(self, entry_time_str: str):
        try:
            entry_time = datetime.fromisoformat(entry_time_str).replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delay = (entry_time - now).total_seconds()
            if delay > 0:
                time.sleep(delay)
        except Exception:
            pass

    def handle_signal(self, signal: Dict[str, Any]):
        if not self.trading_active:
            return
        entry_time = signal.get("entry_time")
        if entry_time:
            self.schedule_trade(entry_time, signal.get("direction", "BUY"), self.base_amount, 0)
        for i, mg_time in enumerate(signal.get("martingale_times", []) or []):
            if i+1 > self.max_martingale:
                break
            mg_amount = self.base_amount * (2 ** (i+1))
            self.schedule_trade(mg_time, signal.get("direction", "BUY"), mg_amount, i+1)

    def handle_command(self, command: str):
        cmd = command.strip().lower()
        if cmd.startswith("/start"):
            self.trading_active = True
        elif cmd.startswith("/stop"):
            self.trading_active = False

    def schedule_trade(self, entry_time: str, direction: str, amount: float, martingale_level: int):
        def execute_trade():
            self.wait_until(entry_time)
            self.place_trade(amount, direction)
        threading.Thread(target=execute_trade, daemon=True).start()

    def place_trade(self, amount: float, direction: str = "BUY"):
        if pyautogui is None:
            return
        try:
            if direction.upper() == "BUY":
                pyautogui.keyDown('shift')
                pyautogui.press('w')
                pyautogui.keyUp('shift')
            elif direction.upper() == "SELL":
                pyautogui.keyDown('shift')
                pyautogui.press('s')
                pyautogui.keyUp('shift')
        except Exception:
            pass

# =========================
# Signal handlers
# =========================
def setup_signal_handlers():
    def signal_handler(signum, frame):
        sys.exit(0)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

# =========================
# Main
# =========================
def main():
    setup_signal_handlers()
    threading.Thread(target=start_health_server, daemon=True).start()
    time.sleep(5)
    driver = setup_driver()
    trade_manager = TradeManager(driver)
    if start_telegram_listener:
        threading.Thread(
            target=start_telegram_listener,
            args=(trade_manager.handle_signal, trade_manager.handle_command),
            daemon=True
        ).start()
    while True:
        time.sleep(30)

if __name__ == "__main__":
    main()
        
