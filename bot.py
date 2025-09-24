import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()
PO_EMAIL = os.getenv("POCKET_EMAIL")
PO_PASS = os.getenv("POCKET_PASS")

def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # DO NOT use headless; manual login required
    # chrome_options.add_argument("--headless")

    try:
        driver = webdriver.Chrome(
            options=chrome_options,
            executable_path="/usr/local/bin/chromedriver"
        )
        print("[INFO] ChromeDriver initialized successfully.")
        return driver
    except Exception as e:
        print("[FATAL] ChromeDriver failed to initialize:", e)
        return None

def safe_quit(driver):
    try:
        if driver:
            driver.quit()
    except Exception:
        pass

def wait_for_manual_login(driver, timeout=600):
    """Wait for manual login to complete. Detect any stable post-login element."""
    print("[INFO] Waiting for manual login...")
    wait = WebDriverWait(driver, timeout)
    try:
        # Replace with an element that always exists after login, e.g., cabinet page
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'cabinet-page')]")))
        print("[SUCCESS] Login detected!")
        return True
    except TimeoutException:
        print("[ERROR] Login not detected within timeout.")
        driver.save_screenshot("login_timeout.png")
        return False

def main():
    driver = init_driver()
    if not driver:
        return

    try:
        print("[INFO] Opening login page...")
        driver.get("https://pocketoption.com/en/login/")

        if not wait_for_manual_login(driver):
            safe_quit(driver)
            return

        print("[INFO] Navigating to demo trading page...")
        driver.get("https://pocketoption.com/en/cabinet/demo-quick-high-low/")

        # Wait for canvas element
        canvas = None
        wait = WebDriverWait(driver, 20)
        for i in range(5):
            try:
                canvas = wait.until(EC.presence_of_element_located((By.TAG_NAME, "canvas")))
                break
            except TimeoutException:
                print(f"[WARN] Canvas not ready yet (attempt {i+1}/5)...")
                time.sleep(3)

        if not canvas:
            print("[ERROR] Canvas not found. Exiting.")
            safe_quit(driver)
            return

        # Canvas & CALL button coordinates
        CALL_X_PERCENT = 0.75
        CALL_Y_PERCENT = 0.85
        canvas_rect = canvas.rect
        call_x = canvas_rect['width'] * CALL_X_PERCENT
        call_y = canvas_rect['height'] * CALL_Y_PERCENT

        print("[SUCCESS] Canvas found. Bot started: auto-clicking CALL every 5 seconds...")

        # Auto-click loop
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
        safe_quit(driver)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"[FATAL] Bot crashed unexpectedly: {e}")
            time.sleep(5)  # wait before restart
    
