"""
Setup Chrome WebDriver for Pocket Option automation.
Fills credentials, clicks Login, detects login completion, and keeps Chrome running
for integration with other modules (e.g., Telegram signal handlers).
Manual CAPTCHA handled via VNC.
"""

import os
import sys
import time
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from dotenv import load_dotenv

# -----------------------
# Force stdout flush
# -----------------------
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("[🟢] bot_setup.py starting...")

# -----------------------
# Load environment variables
# -----------------------
env_path = '/app/.env'
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"[🟢] Loaded environment variables from {env_path}")
else:
    print(f"[⚠️] .env file not found, relying on system environment variables")

# -----------------------
# Environment for Xvfb/VNC
# -----------------------
os.environ['DISPLAY'] = ':1'
os.environ['XAUTHORITY'] = '/tmp/.Xauthority'
if not os.path.exists('/tmp/.Xauthority'):
    open('/tmp/.Xauthority', 'a').close()
    print("[⚠️] Created empty .Xauthority file. Ensure Xvfb is running correctly.")

# -----------------------
# Credentials
# -----------------------
EMAIL = os.getenv("POCKET_EMAIL")
PASSWORD = os.getenv("POCKET_PASS")
if not EMAIL or not PASSWORD:
    print("[❌] Pocket Option email or password is missing.", file=sys.stderr)
    raise ValueError("Missing Pocket Option credentials in environment variables.")

print(f"[🔑] Pocket Option email loaded: {EMAIL}")


def start_driver():
    """
    Starts Chrome WebDriver, logs in to Pocket Option, and returns the driver object
    for other modules (e.g., Telegram handlers) to use.
    """
    driver = None
    try:
        # -----------------------
        # Chrome setup
        # -----------------------
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
        print("[✅] Chrome started and navigated to login page.")

        # -----------------------
        # Fill credentials
        # -----------------------
        try:
            time.sleep(3)  # small buffer for page load
            email_input = driver.find_element(By.NAME, "email")
            password_input = driver.find_element(By.NAME, "password")

            email_input.clear()
            email_input.send_keys(EMAIL)
            password_input.clear()
            password_input.send_keys(PASSWORD)
            print("[✅] Credentials filled. Complete CAPTCHA and login manually via VNC.")

            # -----------------------
            # Click login automatically
            # -----------------------
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            print("[✅] Login button clicked. Waiting for dashboard...")

            # -----------------------
            # Detect login completion dynamically
            # -----------------------
            timeout = 180  # seconds
            poll_interval = 5
            elapsed = 0
            while elapsed < timeout:
                time.sleep(poll_interval)
                elapsed += poll_interval
                current_url = driver.current_url
                if "dashboard" in current_url or "trade" in current_url:
                    print(f"[🟢] Login successful. Redirected to: {current_url}")
                    break
                else:
                    print(f"[⏳] Still on login page... ({elapsed}s elapsed)")
            else:
                print("[⚠️] Login may not have completed. Timeout reached.", file=sys.stderr)

        except NoSuchElementException:
            print("[❌] Could not find login form elements.", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            raise
        except Exception as e:
            print(f"[❌] Error during login process: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            raise

        print("[🟢] Chrome is ready. Returning driver for external control (Telegram signals, etc.).")
        return driver

    except WebDriverException as e:
        print(f"[❌] WebDriver error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        if driver:
            driver.quit()
        raise

    except Exception as e:
        print(f"[❌] Unhandled error occurred: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        if driver:
            driver.quit()
        raise


# -----------------------
# Entry point
# -----------------------
if __name__ == "__main__":
    driver_instance = start_driver()
    try:
        print("[🟢] Press Ctrl+C to exit once manual login/CAPTCHA is done.")
        while True:
            time.sleep(60)  # keep script alive for VNC/manual actions
    except KeyboardInterrupt:
        print("[🔚] Exiting script. Closing Chrome.")
        driver_instance.quit()
