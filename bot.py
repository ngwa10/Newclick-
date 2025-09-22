import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from dotenv import load_dotenv

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def log_exception(e, driver=None):
    url = driver.current_url if driver else "N/A"
    title = driver.title if driver else "N/A"
    log(f"EXCEPTION at URL: {url}, Page title: {title}, Error: {e}")

# --- Load .env ---
load_dotenv()
PO_EMAIL = os.getenv("POCKET_EMAIL")
PO_PASS = os.getenv("POCKET_PASS")

if not PO_EMAIL or not PO_PASS:
    log("ERROR: Pocket Option email or password not set in .env")
    exit(1)

log(".env loaded successfully")

# --- Headless Chrome setup ---
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--window-size=1920,1080")

try:
    driver = webdriver.Chrome(options=chrome_options)
    log("Chrome WebDriver started")
except WebDriverException as e:
    log_exception(e)
    exit(1)

# --- Login ---
try:
    driver.get("https://pocketoption.com/en/login/")
    log("Navigated to Pocket Option login page")
    time.sleep(2)

    # Enter email
    email_field = driver.find_element(By.NAME, "email")
    email_field.send_keys(PO_EMAIL)
    log("Email entered ✅")

    # Enter password
    password_field = driver.find_element(By.NAME, "password")
    password_field.send_keys(PO_PASS)
    log("Password entered ✅")

    # Click login button
    login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
    login_button.click()
    log("Login button clicked ✅")
    time.sleep(5)

    if "cabinet" in driver.current_url or "demo" in driver.current_url:
        log("Login successful ✅")
    else:
        log("Login may have failed ⚠️, check credentials or page")
except Exception as e:
    log_exception(e, driver)
    driver.quit()
    exit(1)

# --- Navigate to demo quick trading ---
try:
    driver.get("https://pocketoption.com/en/cabinet/demo-quick-high-low/")
    log("Navigated to demo quick trading page ✅")
    time.sleep(5)
except Exception as e:
    log_exception(e, driver)
    driver.quit()
    exit(1)

# --- Canvas & CALL button coordinates ---
CALL_X_PERCENT = 0.75  # 75% width
CALL_Y_PERCENT = 0.85  # 85% height

try:
    canvas = driver.find_element(By.TAG_NAME, "canvas")
    log("Canvas element located ✅")
    canvas_rect = canvas.rect
    call_x = canvas_rect['width'] * CALL_X_PERCENT
    call_y = canvas_rect['height'] * CALL_Y_PERCENT
    log(f"CALL button coordinates calculated x={call_x}, y={call_y} ✅")
except NoSuchElementException as e:
    log_exception(e, driver)
    driver.quit()
    exit(1)

log("Bot started: auto-clicking CALL every 5 seconds...")

# --- Auto-click loop ---
try:
    while True:
        driver.execute_script(
            "const canvas=arguments[0]; const x=arguments[1]; const y=arguments[2];"
            "canvas.dispatchEvent(new MouseEvent('mousedown',{clientX:x, clientY:y,bubbles:true}));"
            "canvas.dispatchEvent(new MouseEvent('mouseup',{clientX:x, clientY:y,bubbles:true}));",
            canvas, call_x, call_y
        )
        log(f"CALL clicked at x={call_x}, y={call_y} ✅")
        time.sleep(5)
except KeyboardInterrupt:
    log("Bot stopped manually")
except Exception as e:
    log_exception(e, driver)
finally:
    driver.quit()
    log("Chrome WebDriver closed ✅")
