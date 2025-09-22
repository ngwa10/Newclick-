import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from dotenv import load_dotenv

# --- Load .env ---
load_dotenv()
PO_EMAIL = os.getenv("POCKET_EMAIL")
PO_PASS = os.getenv("POCKET_PASS")

# --- Headless Chrome setup ---
chrome_options = Options()
chrome_options.add_argument("--headless")  # stable headless
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--remote-debugging-port=9222")  # essential in container

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 20)

try:
    # --- Login ---
    print("[INFO] Opening login page...")
    driver.get("https://pocketoption.com/en/login/")

    wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(PO_EMAIL)
    driver.find_element(By.NAME, "password").send_keys(PO_PASS)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    print("[INFO] Login submitted. Waiting for dashboard...")

    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'balance')]")))
        print("[SUCCESS] Logged in successfully!")
    except TimeoutException:
        print("[ERROR] Dashboard did not load in time. Check credentials or page layout.")
        driver.quit()
        exit(1)

    # --- Navigate to demo quick trading ---
    print("[INFO] Opening demo trading page...")
    driver.get("https://pocketoption.com/en/cabinet/demo-quick-high-low/")

    # --- Wait for canvas (retry loop) ---
    canvas = None
    for i in range(5):
        try:
            canvas = wait.until(EC.presence_of_element_located((By.TAG_NAME, "canvas")))
            break
        except TimeoutException:
            print(f"[WARN] Canvas not ready yet (attempt {i+1}/5)...")
            time.sleep(3)

    if not canvas:
        print("[ERROR] Canvas not found after retries. Exiting.")
        driver.quit()
        exit(1)

    # --- Canvas & CALL button coordinates ---
    CALL_X_PERCENT = 0.75
    CALL_Y_PERCENT = 0.85

    canvas_rect = canvas.rect
    call_x = canvas_rect['width'] * CALL_X_PERCENT
    call_y = canvas_rect['height'] * CALL_Y_PERCENT

    print("[SUCCESS] Canvas found. Bot started: auto-clicking CALL every 5 seconds...")

    # --- Auto-click loop ---
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
            print(f"[ERROR] WebDriver exception during click: {e}")
            time.sleep(5)

except Exception as e:
    print(f"[FATAL] Unexpected error: {e}")
finally:
    driver.quit()
