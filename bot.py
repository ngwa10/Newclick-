import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# --- Headless Chrome setup for manual login ---
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--start-maximized")
# Do NOT use headless: we need manual login
# chrome_options.add_argument("--headless")  

# --- Start WebDriver ---
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 30)

try:
    # --- Open login page manually ---
    print("[INFO] Opening login page. Please log in manually...")
    driver.get("https://pocketoption.com/en/login/")

    # --- Wait until user has logged in ---
    logged_in = False
    for i in range(300):  # wait up to ~5 minutes
        try:
            # Check for dashboard element (balance container)
            if wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'balance')]"))):
                logged_in = True
                break
        except TimeoutException:
            pass
        time.sleep(1)
    if not logged_in:
        print("[ERROR] Manual login timeout. Exiting.")
        driver.quit()
        exit(1)

    print("[SUCCESS] Logged in manually! Opening demo trading page...")
    driver.get("https://pocketoption.com/en/cabinet/demo-quick-high-low/")

    # --- Wait for canvas ---
    canvas = None
    for i in range(10):
        try:
            canvas = wait.until(EC.presence_of_element_located((By.TAG_NAME, "canvas")))
            break
        except TimeoutException:
            print(f"[WARN] Canvas not ready yet (attempt {i+1}/10)...")
            time.sleep(2)
    if not canvas:
        print("[ERROR] Canvas not found. Exiting.")
        driver.quit()
        exit(1)

    # --- Calculate CALL button coordinates ---
    CALL_X_PERCENT = 0.75
    CALL_Y_PERCENT = 0.85
    canvas_rect = canvas.rect
    call_x = canvas_rect['width'] * CALL_X_PERCENT
    call_y = canvas_rect['height'] * CALL_Y_PERCENT

    print("[SUCCESS] Canvas found. Bot will auto-click CALL every 5 seconds...")

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
        
