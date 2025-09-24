import os
import time
from datetime import datetime
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


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def init_driver(retries=3):
    for attempt in range(1, retries + 1):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--window-size=1920,1080")
            driver = webdriver.Chrome(options=chrome_options)
            log(f"ChromeDriver initialized (attempt {attempt}).")
            return driver
        except Exception as e:
            log(f"ChromeDriver init failed (attempt {attempt}): {e}")
            time.sleep(5)
    log("ChromeDriver could not be initialized.")
    return None


def safe_quit(driver):
    try:
        if driver:
            driver.quit()
    except Exception:
        pass


def wait_for_manual_login(driver, timeout=600):
    log("Waiting for manual login...")
    wait = WebDriverWait(driver, timeout)
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'cabinet-page')]")))
        log("Login detected!")
        return True
    except TimeoutException:
        log("Manual login not detected within timeout.")
        return False


def main():
    driver = init_driver()
    if not driver:
        return

    try:
        log("Opening login page...")
        driver.get("https://pocketoption.com/en/login/")

        if not wait_for_manual_login(driver):
            log("Exiting due to missing login.")
            safe_quit(driver)
            return

        log("Navigating to demo trading page...")
        driver.get("https://pocketoption.com/en/cabinet/demo-quick-high-low/")

        # Wait for canvas element
        canvas = None
        wait = WebDriverWait(driver, 20)
        for i in range(5):
            try:
                canvas = wait.until(EC.presence_of_element_located((By.TAG_NAME, "canvas")))
                canvas_rect = canvas.rect
                if canvas_rect['width'] < 100 or canvas_rect['height'] < 100:
                    log(f"Canvas too small: {canvas_rect}, exiting.")
                    safe_quit(driver)
                    return
                break
            except TimeoutException:
                log(f"Canvas not ready yet (attempt {i+1}/5)...")
                time.sleep(3)

        if not canvas:
            log("Canvas not found. Exiting.")
            safe_quit(driver)
            return

        call_x = canvas_rect["width"] * 0.75
        call_y = canvas_rect["height"] * 0.85

        log("Canvas ready. Starting auto-click...")

        while True:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", canvas)
                driver.execute_script(
                    "const canvas=arguments[0]; const x=arguments[1]; const y=arguments[2];"
                    "canvas.dispatchEvent(new MouseEvent('mousedown',{clientX:x, clientY:y,bubbles:true}));"
                    "canvas.dispatchEvent(new MouseEvent('mouseup',{clientX:x, clientY:y,bubbles:true}));",
                    canvas,
                    call_x,
                    call_y,
                )
                log("CALL clicked")
                time.sleep(5)
            except WebDriverException as e:
                log(f"Canvas click failed: {e}")
                time.sleep(5)

    except Exception as e:
        log(f"Unexpected error: {e}")
    finally:
        safe_quit(driver)


if __name__ == "__main__":
    # Run main once. Zeabur will restart the container if it fails.
    main()
            
