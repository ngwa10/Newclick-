import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from dotenv import load_dotenv

# Load .env
load_dotenv()
PO_EMAIL = os.getenv("POCKET_EMAIL")
PO_PASS = os.getenv("POCKET_PASS")

# Chrome setup (manual login)
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 25)

try:
    print("[INFO] Please manually log in via the noVNC browser session...")
    driver.get("https://pocketoption.com/en/login/")

    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'balance')]")))
        print("[SUCCESS] Logged in successfully!")
    except TimeoutException:
        print("[ERROR] Dashboard did not load in time. You may need to solve captcha.")
        driver.save_screenshot("login_manual.png")
        exit(1)

    print("[INFO] Opening demo trading page...")
    driver.get("https://pocketoption.com/en/cabinet/demo-quick-high-low/")

    canvas = None
    for i in range(5):
        try:
            canvas = wait.until(EC.presence_of_element_located((By.TAG_NAME, "canvas")))
            break
        except TimeoutException:
            print(f"[WARN] Canvas not ready (attempt {i+1}/5)...")
            time.sleep(3)

    if not canvas:
        print("[ERROR] Canvas not found. Exiting.")
        exit(1)

    CALL_X_PERCENT = 0.75
    CALL_Y_PERCENT = 0.85
    canvas_rect = canvas.rect
    call_x = canvas_rect['width'] * CALL_X_PERCENT
    call_y = canvas_rect['height'] * CALL_Y_PERCENT

    print("[SUCCESS] Canvas found. Bot started (auto-click CALL every 5 seconds)...")

    while True:
        try:
            driver.execute_script(
                "const canvas=arguments[0]; const x=arguments[1]; const y=arguments[2];"
                "canvas.dispatchEvent(new MouseEvent('mousedown',{clientX:x, clientY:y,bubbles:true}));"
                "canvas.dispatchEvent(new MouseEvent('mouseup',{clientX:x, clientY:y,bubbles:true}));",
                canvas, call_x, call_y
            )
            print("[CLICK] CALL clicked")
            time.sleep(5)
        except WebDriverException as e:
            print(f"[ERROR] WebDriver exception: {e}")
            time.sleep(5)

except Exception as e:
    print(f"[FATAL] Unexpected error: {e}")
finally:
    driver.quit()
