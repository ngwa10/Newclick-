import os
import time
import traceback
import sys
import pyautogui
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

print("[🟢] bot.py starting...")

# -----------------------
# Environment and settings
# -----------------------
os.environ['DISPLAY'] = ':1'
os.environ['XAUTHORITY'] = '/tmp/.Xauthority'

if not os.path.exists('/tmp/.Xauthority'):
    open('/tmp/.Xauthority', 'a').close()
    print("[WARN] Created empty .Xauthority file. Ensure Xvfb is running correctly.")

EMAIL = "mylivemyfuture@123gmail.com"
PASSWORD = "AaCcWw3468,"
TRADE_INTERVAL = 10  # seconds between hotkey actions
POST_LOGIN_WAIT = 180 # seconds to wait for manual login (3 minutes)

# -----------------------
# Delay to ensure Xvfb/VNC/Desktop environment is ready
# -----------------------
print("[⌛] Waiting 5 seconds to ensure Xvfb is fully ready...")
time.sleep(5)

# Initialize driver outside try-except for broader scope
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
    # Fill email and password (before manual captcha step)
    # -----------------------
    try:
        time.sleep(3) 
        email_input = driver.find_element(By.NAME, "email")
        password_input = driver.find_element(By.NAME, "password")
        email_input.clear()
        email_input.send_keys(EMAIL)
        password_input.clear()
        password_input.send_keys(PASSWORD)
        print("[✅] Credentials filled. Now you must complete the CAPTCHA and LOGIN MANUALLY via VNC.")
        print(f"[🚨] Waiting {POST_LOGIN_WAIT} seconds for manual login...")
    except NoSuchElementException:
        print("[❌] Error: Could not find email or password input fields. Page layout may have changed.", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise # Re-raise to quit gracefully
    except Exception as e:
        print(f"[❌] Error filling credentials: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise

    # -----------------------
    # Wait for manual login
    # -----------------------
    time.sleep(POST_LOGIN_WAIT)
    print("[🟢] Manual login wait period ended. Assuming logged in.")

    # -----------------------
    # Hotkey automation loop
    # -----------------------
    print("[🚀] Starting hotkey trading loop...")
    
    try:
        screen_width, screen_height = pyautogui.size()
        print(f"[🖼️] PyAutoGUI detected screen resolution: {screen_width}x{screen_height}")
    except Exception as e:
        print(f"[❌] PyAutoGUI could not detect screen size. Is the X server running correctly? Error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise

    while True:
        try:
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"[💓 Heartbeat] Bot alive at {current_time}")

            # --- Sending Hotkeys ---
            pyautogui.keyDown('shift')
            pyautogui.press('d')
            pyautogui.keyUp('shift')
            print(f"[✅ {current_time}] Shift+D pressed (increase trade amount)")

            pyautogui.keyDown('shift')
            pyautogui.press('w')
            pyautogui.keyUp('shift')
            print(f"[✅ {current_time}] Shift+W pressed (buy trade)")

            pyautogui.keyDown('shift')
            pyautogui.press('tab')
            pyautogui.keyUp('shift')
            print(f"[✅ {current_time}] Shift+TAB pressed (next asset)")

            time.sleep(TRADE_INTERVAL)

        except Exception as e:
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"[❌ {current_time}] Error in trading loop: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print("Restarting trading loop in 5 seconds...", file=sys.stderr)
            time.sleep(5)

except WebDriverException as e:
    print(f"[❌] WebDriver error encountered: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    print("This might be due to Chromedriver issues, browser crashes, or the display not being ready.", file=sys.stderr)
except Exception as e:
    print(f"[❌] An unhandled error occurred: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
finally:
    if driver:
        print("[🧹] Quitting Chrome browser.")
        driver.quit()
    print("[🛑] bot.py finished or crashed. Wrapper will restart.")
        
