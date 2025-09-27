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
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any

# =========================
# HARD-CODED CREDENTIALS
# =========================
EMAIL = "mylivemyfuture@123gmail.com"
PASSWORD = "AaCcWw3468,"
TELEGRAM_API_ID = 29630724
TELEGRAM_API_HASH = "8e12421a95fd722246e0c0b194fd3e0c"
TELEGRAM_BOT_TOKEN = "8477806088:AAGEXpIAwN5tNQM0hsCGqP-otpLJjPJLmWA"
TELEGRAM_CHANNEL = "-1003033183667"
WEB_PORT = 8080
NOVNC_PORT = 6080
HEALTH_PORT = 6081  # Changed to avoid conflict with NOVNC
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
            self.send_header('Location', '/vnc.html')  # Redirect fixed
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, format, *args):
        pass  # suppress logs

def start_health_server():
    try:
        logger.info(f"Starting health server on port {HEALTH_PORT}")
        server = HTTPServer(('0.0.0.0', HEALTH_PORT), HealthHandler)
        server.serve_forever()
    except Exception as e:
        logger.error(f"Health server failed to start: {e}")

# =========================
# Xvfb / DISPLAY / PyAutoGUI Setup
# =========================
os.environ.setdefault('DISPLAY', ':1')
xauth_path = '/root/.Xauthority'
if not os.path.exists(xauth_path):
    try:
        open(xauth_path, 'a').close()
        logger.info(f"[✅] Created {xauth_path} file")
    except Exception as e:
        logger.warning(f"[⚠️] Could not create {xauth_path}: {e}")
os.environ['XAUTHORITY'] = xauth_path
time.sleep(1)

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
    try:
        pyautogui.size()
        logger.info("[✅] pyautogui loaded and display accessible")
    except Exception as e:
        logger.warning(f"[⚠️] pyautogui display test failed: {e}")
except Exception as e:
    pyautogui = None
    logger.warning(f"[⚠️] pyautogui not available: {e}")

# =========================
# Selenium Optional Setup
# =========================
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    logger.info("Selenium imports successful")
except Exception as e:
    webdriver = None
    logger.warning(f"Selenium not available: {e}")

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
# Trade Manager
# =========================
class TradeManager:
    def __init__(self, driver: Optional[webdriver.Chrome] = None,
                 base_amount: float = 1.0, max_martingale: int = 2):
        self.trading_active = False
        self.driver = driver
        self.base_amount = base_amount
        self.max_martingale = max_martingale
        self.current_martingale_count = 0
        self.current_pair = None

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
        if signal.get("timezone", "OTC-3") == "OTC-4":
            fmt = "%H:%M:%S" if len(entry_time.split(":")) == 3 else "%H:%M"
            dt = datetime.strptime(entry_time, fmt)
            dt += timedelta(hours=1)  # Convert to OTC-3
            entry_time = dt.strftime(fmt)
            signal['entry_time'] = entry_time

        if entry_time:
            self.schedule_trade(entry_time, signal.get("direction", "BUY"), self.base_amount, 0)

        for i, mg_time in enumerate(signal.get("martingale_times", []) or []):
            if i + 1 > self.max_martingale:
                break
            mg_amount = self.base_amount * (2 ** (i + 1))
            self.schedule_trade(mg_time, signal.get("direction", "BUY"), mg_amount, i + 1)

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
# Signal Handlers
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
    trade_manager = TradeManager()
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
          
