# core.py
"""
Core logic for Pocket Option Telegram Trading Bot.
Includes: main bot orchestrator, trade manager, Telegram listener, hotkey control, result detection.
"""

import os
import time
import traceback
import sys
from dotenv import load_dotenv  # <-- Load .env
import pyautogui
import pytesseract
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException

# -----------------------
# Force stdout flush so logs show immediately
# -----------------------
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("[🟢] core.py starting...")

# -----------------------
# Load environment variables from .env
# -----------------------
ENV_PATH = "/app/.env"
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
    print(f"[🟢] Loaded environment variables from {ENV_PATH}")
else:
    print(f"[❌] .env file not found at {ENV_PATH}", file=sys.stderr)

# -----------------------
# Telegram credentials
# -----------------------
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL")

# Verify Telegram credentials
if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL]):
    raise ValueError("[❌] Missing Telegram environment variables. Please check .env file.")

print("[🔑] Telegram API ID: SET")
print("[🔑] Telegram API HASH: SET")
print("[🔑] Telegram BOT TOKEN: SET")
print(f"[🔑] Telegram CHANNEL: {TELEGRAM_CHANNEL}")

# Now safe to import Telegram integration
from telegram_integration import start_telegram_listener, parse_signal

# -----------------------
# Environment for Xvfb/VNC
# -----------------------
os.environ['DISPLAY'] = ':1'
os.environ['XAUTHORITY'] = '/tmp/.Xauthority'

if not os.path.exists('/tmp/.Xauthority'):
    open('/tmp/.Xauthority', 'a').close()
    print("[WARN] Created empty .Xauthority file. Ensure Xvfb is running correctly.")

# -----------------------
# Pocket Option credentials
# -----------------------
EMAIL = os.getenv("POCKET_EMAIL", "mylivemyfuture@123gmail.com")
PASSWORD = os.getenv("POCKET_PASS", "AaCcWw3468,")
POST_LOGIN_WAIT = 180  # seconds to wait for manual login

# -----------------------
# Selenium Chrome driver setup
# -----------------------
def setup_driver():
    print("[⌛] Waiting 5 seconds to ensure Xvfb/VNC is ready...")
    time.sleep(5)
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-data-dir=/tmp/chrome-user-data")

        service = Service("/usr/local/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://pocketoption.com/en/login/")
        print("[✅] Chrome started successfully and navigated to login page.")

        # Fill credentials for manual login
        try:
            time.sleep(3)
            email_input = driver.find_element(By.NAME, "email")
            password_input = driver.find_element(By.NAME, "password")
            email_input.clear()
            email_input.send_keys(EMAIL)
            password_input.clear()
            password_input.send_keys(PASSWORD)
            print("[✅] Credentials filled. Complete CAPTCHA and login manually via VNC.")
            print(f"[🚨] Waiting {POST_LOGIN_WAIT} seconds for manual login...")
        except NoSuchElementException:
            print("[❌] Could not find email or password input fields. Page layout may have changed.", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            raise
        except Exception as e:
            print(f"[❌] Error filling credentials: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            raise

        time.sleep(POST_LOGIN_WAIT)
        print("[🟢] Manual login wait period ended. Assuming logged in.")
        return driver

    except WebDriverException as e:
        print(f"[❌] WebDriver error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise
    except Exception as e:
        print(f"[❌] Unhandled error occurred: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise

# -----------------------
# Trade Manager
# -----------------------
class TradeManager:
    def __init__(self, driver):
        self.trading_active = False
        self.martingale_level = 0
        self.base_amount = 1  # TODO: Load from config or env
        self.max_martingale = 2  # Default to 2 for Anna signals
        self.driver = driver

    def handle_signal(self, signal):
        if not self.trading_active:
            print("[⏸️] Trading paused. Signal ignored.")
            return

        # Selenium selects currency and timeframe (assumes functions exist)
        from selenium_integration import select_currency_pair, select_timeframe
        select_currency_pair(self.driver, signal['currency_pair'])
        select_timeframe(self.driver, signal['timeframe'])
        print(f"[⚡] Ready for trade: {signal}")

        self.schedule_trade(signal['entry_time'], signal['direction'], self.base_amount, martingale_level=0)
        for i, mg_time in enumerate(signal['martingale_times']):
            self.schedule_trade(mg_time, signal['direction'], self.base_amount * (2 ** (i+1)), martingale_level=i+1)

    def handle_command(self, command):
        if command.startswith("/start"):
            self.trading_active = True
            print("[🚀] Trading started by user command.")
        elif command.startswith("/stop"):
            self.trading_active = False
            print("[⏹️] Trading stopped by user command.")

    def schedule_trade(self, entry_time, direction, amount, martingale_level):
        print(f"[⏰] Scheduling trade at {entry_time} | {direction} | amount: {amount} | level: {martingale_level}")
        # TODO: Implement scheduling and execution logic

    def place_trade(self, amount=None, direction="BUY"):
        # Hotkey automation (triggered only on signal)
        if direction.upper() == "BUY":
            pyautogui.keyDown('shift'); pyautogui.press('w'); pyautogui.keyUp('shift')
        elif direction.upper() == "SELL":
            pyautogui.keyDown('shift'); pyautogui.press('s'); pyautogui.keyUp('shift')
        print(f"[🎯] Trade placed: {direction} | amount: {amount}")

# -----------------------
# Main Bot
# -----------------------
def main():
    driver = setup_driver()
    trade_manager = TradeManager(driver)
    start_telegram_listener(trade_manager.handle_signal, trade_manager.handle_command)
    print("[🟢] Bot started! Waiting for signals...")

    try:
        while True:
            time.sleep(1)  # keep alive, trading is event-driven via Telegram signals
    except KeyboardInterrupt:
        print("[🛑] Bot stopped by user.")
    finally:
        if driver:
            print("[🧹] Quitting Chrome browser.")
            driver.quit()
        print("[🛑] core.py finished.")

if __name__ == "__main__":
    main()
