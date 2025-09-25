import os
import time
import traceback
import pyautogui
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# -----------------------
# Environment and settings
# -----------------------
os.environ['DISPLAY'] = ':1'

EMAIL = "mylivemyfuture@123gmail.com"
PASSWORD = "AaCcWw3468,"
TRADE_INTERVAL = 10  # seconds
POST_LOGIN_WAIT = 60  # wait after manual login

# -----------------------
# Small delay to ensure Xvfb/X11 is ready
# -----------------------
time.sleep(2)

# -----------------------
# Start Chrome with Selenium
# -----------------------
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
chrome_options.add_argument("--user-data-dir=/tmp/chrome-user-data")

service = Service("/usr/local/bin/chromedriver")

try:
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://pocketoption.com/en/login/")
    print("[✅] Chrome started successfully")
except Exception:
    print("[❌] Selenium failed to start Chrome:")
    traceback.print_exc()
    raise

# -----------------------
# Fill email and password
# -----------------------
try:
    email_input = driver.find_element("name", "email")
    password_input = driver.find_element("name", "password")
    email_input.clear()
    email_input.send_keys(EMAIL)
    password_input.clear()
    password_input.send_keys(PASSWORD)
    print("[✅] Credentials filled. Please click login manually.")
except Exception:
    print("[❌] Error filling credentials:")
    traceback.print_exc()

# Wait for manual login
time.sleep(POST_LOGIN_WAIT)

# -----------------------
# Hotkey automation loop
# -----------------------
print("[🚀] Starting hotkey trading loop...")

while True:
    try:
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[💓 Heartbeat] Bot alive at {current_time}")

        # Shift + D → increase trade amount
        pyautogui.keyDown('shift')
        pyautogui.press('d')
        pyautogui.keyUp('shift')
        print(f"[✅ {current_time}] Shift+D pressed")

        # Shift + W → buy trade
        pyautogui.keyDown('shift')
        pyautogui.press('w')
        pyautogui.keyUp('shift')
        print(f"[✅ {current_time}] Shift+W pressed")

        # Shift + TAB → next asset
        pyautogui.keyDown('shift')
        pyautogui.press('tab')
        pyautogui.keyUp('shift')
        print(f"[✅ {current_time}] Shift+TAB pressed")

        time.sleep(TRADE_INTERVAL)

    except Exception:
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[❌ {current_time}] Error in trading loop:")
        traceback.print_exc()
        time.sleep(5)
    
