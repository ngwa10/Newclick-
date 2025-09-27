# core.py
"""
Core logic for Pocket Option Telegram Trading Bot.
Includes: main bot orchestrator, trade manager, Telegram listener, hotkey control, and trade execution logic.
"""

import os
import sys
import time
import traceback
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List

# Optional GUI automation / OCR libraries
try:
    import pyautogui
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
from selenium.common.exceptions import WebDriverException, NoSuchElementException

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

# Telegram environment variables
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL")

if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL]):
    raise ValueError("[❌] Missing Telegram environment variables. Check .env file or environment.")

print("[🔑] Telegram configuration loaded.")

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

# Pocket Option credentials
EMAIL = os.getenv("POCKET_EMAIL")
PASSWORD = os.getenv("POCKET_PASS")
try:
    POST_LOGIN_WAIT = int(os.getenv("POST_LOGIN_WAIT", "180"))
except ValueError:
    POST_LOGIN_WAIT = 180

if not EMAIL or not PASSWORD:
    print("[⚠️] Pocket Option credentials not set in environment variables.", file=sys.stderr)

# -------------------------------------------------------
# Setup Chrome WebDriver
# -------------------------------------------------------
def setup_driver(chromedriver_path: str = "/usr/local/bin/chromedriver", headless: bool = False,
                 user_data_dir: str = "/tmp/chrome-user-data") -> Optional[webdriver.Chrome]:
    """
    Launch Chrome WebDriver and navigate to Pocket Option login page.
    Returns the Selenium WebDriver instance or None if failed.
    """
    time.sleep(2)  # ensure Xvfb/VNC is ready
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
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://pocketoption.com/en/login/")
        print("[✅] Chrome started and navigated to login page.")
    except WebDriverException as e:
        print(f"[❌] WebDriver error when starting Chrome: {e}", file=sys.stderr)
        traceback.print_exc()
        return None

    # Autofill credentials if available
    if EMAIL and PASSWORD:
        try:
            time.sleep(2)
            email_input = driver.find_element(By.NAME, "email")
            password_input = driver.find_element(By.NAME, "password")
            email_input.clear()
            email_input.send_keys(EMAIL)
            password_input.clear()
            password_input.send_keys(PASSWORD)
            print("[✅] Credentials filled. Complete CAPTCHA manually if required.")
            print(f"[🚨] Waiting {POST_LOGIN_WAIT} seconds for manual login...")
        except Exception as e:
            print(f"[⚠️] Could not fill credentials: {e}", file=sys.stderr)
    return driver

# -------------------------------------------------------
# Trade Manager
# -------------------------------------------------------
class TradeManager:
    def __init__(self, driver: Optional[webdriver.Chrome] = None, base_amount: float = 1.0, max_martingale: int = 2):
        self.trading_active = False
        self.martingale_level = 0
        self.base_amount = base_amount
        self.max_martingale = max_martingale
        self.driver = driver

    def handle_signal(self, signal: Dict[str, Any]):
        if not self.trading_active:
            print("[⏸️] Trading paused. Signal ignored.")
            return

        try:
            from selenium_integration import select_currency_pair, select_timeframe  # type: ignore
        except Exception:
            select_currency_pair = None
            select_timeframe = None
            print("[⚠️] selenium_integration module not available.", file=sys.stderr)

        if select_currency_pair and select_timeframe and self.driver:
            try:
                select_currency_pair(self.driver, signal.get('currency_pair'))
                select_timeframe(self.driver, signal.get('timeframe'))
            except Exception as e:
                print(f"[❌] Error selecting pair/timeframe: {e}", file=sys.stderr)
                traceback.print_exc()

        print(f"[⚡] Ready for trade: {signal}")

        self.schedule_trade(signal.get('entry_time'), signal.get('direction'), self.base_amount, 0)
        for i, mg_time in enumerate(signal.get('martingale_times', []) or []):
            if i + 1 > self.max_martingale:
                print(f"[⚠️] Martingale level {i+1} exceeds max {self.max_martingale}; skipping.")
                break
            amount = self.base_amount * (2 ** (i + 1))
            self.schedule_trade(mg_time, signal.get('direction'), amount, i + 1)

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

    def schedule_trade(self, entry_time: Optional[str], direction: str, amount: float, martingale_level: int):
        print(f"[⏰] Scheduling trade at {entry_time} | {direction} | amount: {amount} | level: {martingale_level}")
        if not entry_time:
            try:
                self.place_trade(amount, direction)
            except Exception as e:
                print(f"[❌] Failed to place immediate trade: {e}", file=sys.stderr)
                traceback.print_exc()
        else:
            print("[⚠️] entry_time provided but scheduling not implemented.")

    def place_trade(self, amount: float, direction: str = "BUY"):
        print(f"[🎯] Attempting trade: {direction} | amount: {amount}")
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
            time.sleep(1)
    except KeyboardInterrupt:
        print("[🛑] Bot stopped by user.")
    finally:
        if driver:
            try:
                print("[🧹] Quitting Chrome browser.")
                driver.quit()
            except Exception as e:
                print(f"[⚠️] Error quitting driver: {e}", file=sys.stderr)
        print("[🛑] core.py finished.")


if __name__ == "__main__":
    main()
