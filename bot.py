# bot_setup.py
"""
Setup Chrome WebDriver for Pocket Option automation.
Loads credentials from .env and ensures Xvfb/VNC environment is ready.
"""

import os
import time
import traceback
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from dotenv import load_dotenv

# -----------------------
# Force stdout flush so logs show immediately
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
    print(f"[⚠️] .env file not found at {env_path}, relying on system environment variables")

# -----------------------
# Environment variables for Xvfb/VNC
# -----------------------
os.environ['DISPLAY'] = ':1'
os.environ['XAUTHORITY'] = '/tmp/.Xauthority'

if not os.path.exists('/tmp/.Xauthority'):
    open('/tmp/.Xauthority', 'a').close()
    print("[WARN] Created empty .Xauthority file. Ensure Xvfb is running correctly.")

# -----------------------
# Credentials and settings
# -----------------------
EMAIL = os.getenv("POCKET_EMAIL")
PASSWORD = os.getenv("POCKET_PASS")
POST_LOGIN_WAIT = int(os.getenv("POST_LOGIN_WAIT", 180))

if not EMAIL or not PASSWORD:
    print("[❌] Pocket Option email or password is missing. Check your .env file.")
    raise ValueError("Missing Pocket Option credentials in environment variables.")

print(f"[🔑] Pocket Option email loaded: {EMAIL}")

# -----------------------
# Delay to ensure Xvfb/VNC/Desktop environment is ready
# -----------------------
print("[⌛] Waiting 5 seconds to ensure Xvfb/VNC is ready...")
time.sleep(5)

driver = None

try:
    # -----------------------
    # Start Chrome with Selenium
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
    print("[✅] Chrome started successfully and navigated to login page.")

    # -----------------------
    # Fill email and password (manual CAPTCHA required)
    # -----------------------
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

except WebDriverException as e:
    print(f"[❌] WebDriver error: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    raise
except Exception as e:
    print(f"[❌] Unhandled error occurred: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    raise
finally:
    print("[🟢] bot_setup.py finished. Chrome driver is ready for further automation.")
