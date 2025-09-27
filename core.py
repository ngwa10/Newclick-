# core.py
"""
Core logic for Pocket Option Telegram Trading Bot.
Includes: main bot orchestrator, trade manager, Telegram listener, hotkey control, and trade execution logic.
"""

import os
import sys
import time
import traceback
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Optional, Dict, Any

# Optional GUI automation / OCR libraries
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
except Exception:
    pyautogui = None

try:
    import pytesseract
except Exception:
    pytesseract = None

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

# Configure line buffering
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

print("[🟢] core.py starting...")

# --- Load environment variables ---
ENV_PATH = ".env"
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
    print(f"[🟢] Loaded environment variables from {ENV_PATH}")
else:
    print(f"[⚠️] .env file not found at {ENV_PATH} — falling back to environment variables", file=sys.stderr)

# Pocket Option credentials
EMAIL = os.getenv("POCKET_EMAIL")
PASSWORD = os.getenv("POCKET_PASS")
try:
    POST_LOGIN_WAIT = int(os.getenv("POST_LOGIN_WAIT", "180"))
except ValueError:
    POST_LOGIN_WAIT = 180

if not EMAIL or not PASSWORD:
    print("[⚠️] Pocket Option credentials not set in environment variables.", file=sys.stderr)

# Telegram environment variables
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL")

if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL]):
    print("[⚠️] Missing Telegram environment variables. Telegram listener may not start.", file=sys.stderr)

# Local import for Telegram integration
try:
    from telegram_integration import start_telegram_listener, parse_signal  # type: ignore
except Exception:
    start_telegram_listener = None
    parse_signal = None
    print("[⚠️] telegram_integration module not found. Telegram listener will not start.", file=sys.stderr)

# --- Display/Xvfb Setup ---
os.environ.setdefault('DISPLAY', ':1')
os.environ.setdefault('XAUTHORITY', '/tmp/.Xauthority')
if not os.path.exists('/tmp/.Xauthority'):
    open('/tmp/.Xauthority', 'a').close()
    print("[⚠️] Created empty /tmp/.Xauthority. Ensure Xvfb is running if GUI is required.")

# -------------------------------------------------------
# Setup Chrome WebDriver
# -------------------------------------------------------
def setup_driver(chromedriver_path: str = "/usr/local/bin/chromedriver", headless: bool = False,
                 user_data_dir: str = "/tmp/chrome-user-data") -> Optional[webdriver.Chrome]:
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    if headless:
        chrome_options.add_argument("--headless=new")

    service = Service(chromedriver_path)
    
    for attempt in range(3):
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get("https://pocketoption.com/en/login/")
            print("[✅] Chrome started and navigated to login page.")
            if EMAIL and PASSWORD:
                try:
                    time.sleep(2)
                    email_input = driver.find_element(By.NAME, "email")
                    password_input = driver.find_element(By.NAME, "password")
                    email_input.clear()
                    email_input.send_keys(EMAIL)
                    password_input.clear()
                    password_input.send_keys(PASSWORD)
                    print(f"[🚨] Waiting {POST_LOGIN_WAIT} seconds for manual login / CAPTCHA")
                    time.sleep(POST_LOGIN_WAIT)
                except Exception as e:
                    print(f"[⚠️] Could not autofill credentials: {e}", file=sys.stderr)
            return driver
        except WebDriverException as e:
            print(f"[❌] WebDriver attempt {attempt+1} failed: {e}", file=sys.stderr)
            time.sleep(3)
    return None

# -------------------------------------------------------
# Trade Manager
# -------------------------------------------------------
class TradeManager:
    def __init__(self, driver: Optional[webdriver.Chrome] = None, base_amount: float = 1.0, max_martingale: int = 2):
        self.trading_active = False
        self.driver = driver
        self.base_amount = base_amount
        self.max_martingale = max_martingale

    # Helper to wait until a specific entry time
    def wait_until(self, entry_time_str: str):
        try:
            entry_time = datetime.fromisoformat(entry_time_str).replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delay = (entry_time - now).total_seconds()
            if delay > 0:
                print(f"[⏰] Waiting {delay:.2f} seconds until trade entry time")
                time.sleep(delay)
        except Exception as e:
            print(f"[⚠️] Invalid entry_time format '{entry_time_str}': {e}", file=sys.stderr)

    def handle_signal(self, signal: Dict[str, Any]):
        if not self.trading_active:
            print("[⏸️] Trading paused. Signal ignored.")
            return

        # Schedule direct trade at entry_time
        entry_time = signal.get("entry_time")
        if entry_time:
            self.schedule_trade(entry_time, signal.get("direction", "BUY"), self.base_amount, 0)
        else:
            print("[⚠️] Signal missing entry_time, skipping direct trade")

        # Schedule martingale trades
        for i, mg_time in enumerate(signal.get("martingale_times", []) or []):
            if i + 1 > self.max_martingale:
                print(f"[⚠️] Martingale level {i+1} exceeds max {self.max_martingale}; skipping.")
                break
            mg_amount = self.base_amount * (2 ** (i + 1))
            self.schedule_trade(mg_time, signal.get("direction", "BUY"), mg_amount, i + 1)

    def handle_command(self, command: str):
        cmd = command.strip().lower()
        if cmd.startswith("/start"):
            self.trading_active = True
            print("[🚀] Trading started by user command.")
        elif cmd.startswith("/stop"):
            self.trading_active = False
            print("[⏹️] Trading stopped by user command.")
        else:
            print(f"[ℹ️] Unknown command: {command}")

    # Schedule trade to run at exact entry time
    def schedule_trade(self, entry_time: str, direction: str, amount: float, martingale_level: int):
        print(f"[⚡] Scheduling trade at {entry_time} | {direction} | amount: {amount} | level: {martingale_level}")
        self.wait_until(entry_time)
        self.place_trade(amount, direction)

    def place_trade(self, amount: float, direction: str = "BUY"):
        print(f"[🎯] Placing trade: {direction} | amount: {amount}")
        if pyautogui is None:
            print("[⚠️] pyautogui not available; implement Selenium click fallback.", file=sys.stderr)
            return
        try:
            direction_upper = direction.upper()
            if direction_upper == "BUY":
                pyautogui.keyDown('shift'); pyautogui.press('w'); pyautogui.keyUp('shift')
            elif direction_upper == "SELL":
                pyautogui.keyDown('shift'); pyautogui.press('s'); pyautogui.keyUp('shift')
            else:
                print(f"[⚠️] Unknown direction '{direction}'. Use BUY/SELL.")
                return
            print(f"[✅] Trade hotkey sent: {direction} | amount: {amount}")
        except Exception as e:
            print(f"[❌] Error sending trade hotkeys: {e}", file=sys.stderr)
            traceback.print_exc()

# -------------------------------------------------------
# Main Entry
# -------------------------------------------------------
def main():
    driver = setup_driver()
    trade_manager = TradeManager(driver)

    if start_telegram_listener:
        try:
            start_telegram_listener(trade_manager.handle_signal, trade_manager.handle_command)
            print("[🟢] Telegram listener started.")
        except Exception as e:
            print(f"[❌] Telegram listener failed: {e}", file=sys.stderr)
            traceback.print_exc()
    else:
        print("[⚠️] Telegram listener not available; skipping.", file=sys.stderr)

    print("[🟢] Bot started! Waiting for signals...")
    try:
        while True:
            time.sleep(1
    
