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

# Optional GUI automation / OCR libraries (used at runtime if available)
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

# Attempt to configure line buffering (works on Python 3.7+)
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    # ignore if not available
    pass

print("[🟢] core.py starting...")

# --- Load environment variables ---
ENV_PATH = ".env"
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
    print(f"[🟢] Loaded environment variables from {ENV_PATH}")
else:
    print(f"[⚠️] .env file not found at {ENV_PATH} — falling back to environment variables", file=sys.stderr)

TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL")

if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL]):
    raise ValueError("[❌] Missing Telegram environment variables. Please check .env file or environment.")

print("[🔑] Telegram API ID: SET")
print("[🔑] Telegram API HASH: SET")
print("[🔑] Telegram BOT TOKEN: SET")
print(f"[🔑] Telegram CHANNEL: {TELEGRAM_CHANNEL}")

# Local import for Telegram integration - user must provide telegram_integration.py
# Expected: start_telegram_listener(signal_callback, command_callback)
try:
    from telegram_integration import start_telegram_listener, parse_signal  # type: ignore
except Exception:
    # If the module isn't present, notify and continue; runtime will fail when listener is started.
    start_telegram_listener = None
    parse_signal = None
    print("[⚠️] telegram_integration module not found. Telegram listener will not start.", file=sys.stderr)

# --- Display/Xvfb Setup (for headless servers) ---
os.environ.setdefault('DISPLAY', ':1')
os.environ.setdefault('XAUTHORITY', '/tmp/.Xauthority')

if not os.path.exists('/tmp/.Xauthority'):
    # create empty file if it doesn't exist (some environments expect it)
    try:
        open('/tmp/.Xauthority', 'a').close()
        print("[⚠️] Created empty /tmp/.Xauthority. Ensure Xvfb is running if GUI is required.")
    except Exception as e:
        print(f"[❌] Could not create /tmp/.Xauthority: {e}", file=sys.stderr)

# --- Pocket Option credentials (use environment variables; do NOT hardcode in production) ---
EMAIL = os.getenv("POCKET_EMAIL")
PASSWORD = os.getenv("POCKET_PASS")
POST_LOGIN_WAIT = int(os.getenv("POST_LOGIN_WAIT", "180"))  # seconds to wait for manual login (CAPTCHA)

if not EMAIL or not PASSWORD:
    print("[⚠️] Pocket Option credentials not set in environment variables. setup_driver will fail if attempted.", file=sys.stderr)

# -------------------------------------------------------
# 🧠 Setup Chrome WebDriver
# -------------------------------------------------------
def setup_driver(chromedriver_path: str = "/usr/local/bin/chromedriver", headless: bool = False, user_data_dir: str = "/tmp/chrome-user-data"):
    """
    Launch Chrome WebDriver and navigate to Pocket Option login page.
    Returns the Selenium WebDriver instance.
    """
    print("[⌛] Waiting 2 seconds to ensure Xvfb/VNC is ready...")
    time.sleep(2)

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
        print("[✅] Chrome started successfully and navigated to Pocket Option login page.")
    except WebDriverException as e:
        print(f"[❌] WebDriver error when starting Chrome: {e}", file=sys.stderr)
        traceback.print_exc()
        raise

    # Try to fill credentials if present
    if EMAIL and PASSWORD:
        try:
            time.sleep(2)
            email_input = driver.find_element(By.NAME, "email")
            password_input = driver.find_element(By.NAME, "password")

            email_input.clear()
            email_input.send_keys(EMAIL)
            password_input.clear()
            password_input.send_keys(PASSWORD)

            print("[✅] Credentials filled. Complete CAPTCHA and login manually if required.")
            print(f"[🚨] Waiting {POST_LOGIN_WAIT} seconds for manual login (CAPTCHA/2FA)...")
        except NoSuchElementException:
            print("[⚠️] Could not find email or password input fields on the page. You may need to update selectors.", file=sys.stderr)
        except Exception as e:
            print(f"[❌] Error filling credentials: {e}", file=sys.stderr)
            traceback.print_exc()
    else:
        print("[⚠️] Email/password not provided; skipping autofill.", file=sys.stderr)

    # Wait for user to complete manual login (if necessary)
    try:
        time.sleep(POST_LOGIN_WAIT)
        print("[🟢] Manual login wait period ended. Assuming logged in (verify in VNC/browser).")
    except KeyboardInterrupt:
        print("[🛑] Manual login wait interrupted by user.")
    return driver

# -------------------------------------------------------
# 📈 Trade Manager Class
# -------------------------------------------------------
class TradeManager:
    def __init__(self, driver=None, base_amount: float = 1.0, max_martingale: int = 2):
        self.trading_active = False
        self.martingale_level = 0
        self.base_amount = base_amount
        self.max_martingale = max_martingale
        self.driver = driver

    def handle_signal(self, signal: dict):
        """
        Expected `signal` structure (example):
        {
            "currency_pair": "EURUSD",
            "timeframe": "1m",
            "entry_time": "2025-09-26T12:34:56Z",  # or epoch, or another agreed format
            "direction": "BUY",  # or "SELL"
            "martingale_times": ["2025-09-26T12:35:56Z", ...]
        }
        """
        if not self.trading_active:
            print("[⏸️] Trading paused. Signal ignored.")
            return

        # Delegated UI interactions assumed to be in selenium_integration.py
        try:
            from selenium_integration import select_currency_pair, select_timeframe  # type: ignore
        except Exception:
            select_currency_pair = None
            select_timeframe = None
            print("[⚠️] selenium_integration module not available — UI helpers missing.", file=sys.stderr)

        if select_currency_pair and select_timeframe and self.driver:
            try:
                select_currency_pair(self.driver, signal.get('currency_pair'))
                select_timeframe(self.driver, signal.get('timeframe'))
            except Exception as e:
                print(f"[❌] Error selecting pair/timeframe: {e}", file=sys.stderr)
                traceback.print_exc()

        print(f"[⚡] Ready for trade: {signal}")

        # Schedule main entry
        self.schedule_trade(signal.get('entry_time'), signal.get('direction'), self.base_amount, martingale_level=0)

        # Schedule martingale trades if any
        for i, mg_time in enumerate(signal.get('martingale_times', []) or []):
            amount = self.base_amount * (2 ** (i + 1))
            if i + 1 > self.max_martingale:
                print(f"[⚠️] Martingale level {i+1} exceeds max_martingale ({self.max_martingale}); skipping further mg steps.")
                break
            self.schedule_trade(mg_time, signal.get('direction'), amount, martingale_level=i + 1)

    def handle_command(self, command: str):
        """
        Expected commands:
        - "/start" => enable trading
        - "/stop"  => disable trading
        - other commands may be added by the user
        """
        cmd = command.strip().lower()
        if cmd.startswith("/start"):
            self.trading_active = True
            print("[🚀] Trading started by user command.")
        elif cmd.startswith("/stop"):
            self.trading_active = False
            print("[⏹️] Trading stopped by user command.")
        else:
            print(f"[ℹ️] Received unknown command: {command}")

    def schedule_trade(self, entry_time, direction: str, amount: float, martingale_level: int = 0):
        """
        Placeholder scheduling logic. For production use, replace with precise scheduling
        that parses entry_time and schedules a job (e.g., sched, APScheduler, threading.Timer).
        For now, we'll print a message and attempt to place a trade immediately if entry_time is None.
        """
        print(f"[⏰] Scheduling trade at {entry_time} | {direction} | amount: {amount} | level: {martingale_level}")
        # If entry_time is None, place the trade immediately (useful for testing)
        if not entry_time:
            try:
                self.place_trade(amount=amount, direction=direction)
            except Exception as e:
                print(f"[❌] Failed to place immediate trade: {e}", file=sys.stderr)
                traceback.print_exc()
        else:
            # TODO: Implement proper scheduling here (e.g., APScheduler)
            print("[⚠️] schedule_trade: entry_time provided but scheduling not implemented. Implement scheduling logic.")

    def place_trade(self, amount: float = None, direction: str = "BUY"):
        """
        Place a trade using pyautogui hotkeys (if available).
        This method should be adapted to the actual platform controls or Selenium clicks.
        """
        print(f"[🎯] Attempting to place trade: {direction} | amount: {amount}")

        if pyautogui is None:
            print("[⚠️] pyautogui not available; cannot send hotkeys. Implement Selenium click fallback.", file=sys.stderr)
            return

        direction_upper = (direction or "BUY").upper()
        try:
            if direction_upper == "BUY":
                pyautogui.keyDown('shift')
                pyautogui.press('w')
                pyautogui.keyUp('shift')
            elif direction_upper == "SELL":
                pyautogui.keyDown('shift')
                pyautogui.press('s')
                pyautogui.keyUp('shift')
            else:
                print(f"[⚠️] Unknown direction '{direction}'. Use 'BUY' or 'SELL'.")
                return
            print(f"[✅] Trade hotkey sequence sent: {direction} | amount: {amount}")
        except Exception as e:
            print(f"[❌] Error sending hotkeys for trade: {e}", file=sys.stderr)
            traceback.print_exc()

# -------------------------------------------------------
# 🚀 Main Entry Point
# -------------------------------------------------------
def main():
    driver = None
    try:
        # Try to create a driver (will raise if chromedriver not available)
        driver = setup_driver()
    except Exception as e:
        print(f"[⚠️] setup_driver failed: {e}. Continuing without Selenium driver (useful for dry-run/testing).", file=sys.stderr)
        driver = None

    trade_manager = TradeManager(driver=driver)

    # Start Telegram listener if available
    if start_telegram_listener is not None:
        try:
            # The listener should call trade_manager.handle_signal for signals
            # and trade_manager.handle_command for text commands.
            start_telegram_listener(trade_manager.handle_signal, trade_manager.handle_command)
            print("[🟢] Telegram listener started.")
        except Exception as e:
            print(f"[❌] Failed to start Telegram listener: {e}", file=sys.stderr)
            traceback.print_exc()
    else:
        print("[⚠️] Telegram listener not available; skipping listener startup.", file=sys.stderr)

    print("[🟢] Bot started! Waiting for signals... (Press Ctrl+C to stop)")

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
