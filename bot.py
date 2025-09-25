import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
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
            # chrome_options.add_argument("--headless=new")  # optional

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

def fill_login_form(driver):
    log("Opening login page...")
    driver.get("https://pocketoption.com/en/login/")

    wait = WebDriverWait(driver, 20)
    try:
        # Wait for email input field
        email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
        password_input = driver.find_element(By.NAME, "password")

        # Input credentials
        email_input.clear()
        email_input.send_keys(PO_EMAIL)
        password_input.clear()
        password_input.send_keys(PO_PASS)

        log("Email and password filled. Please complete any verification and click LOGIN manually.")
        return True
    except TimeoutException:
        log("Login fields not found. Exiting.")
        return False

def wait_for_manual_login(driver, timeout=600):
    log("Waiting for manual login...")
    wait = WebDriverWait(driver, timeout)
    try:
        wait.until(EC.url_contains("/cabinet"))
        log("Manual login detected!")
        return True
    except TimeoutException:
        log(f"Manual login not detected within {timeout} seconds. Last URL: {driver.current_url}")
        return False

def main():
    driver = init_driver()
    if not driver:
        return

    try:
        if not fill_login_form(driver):
            safe_quit(driver)
            return

        # Wait until you manually log in
        if not wait_for_manual_login(driver):
            safe_quit(driver)
            return

        # Navigate to demo trading page
        log("Navigating to demo trading page...")
        driver.get("https://pocketoption.com/en/cabinet/demo-quick-high-low/")

        # Wait for CALL button element
        wait = WebDriverWait(driver, 20)
        try:
            call_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".quick-trade-button-call"))) 
            log("CALL button found. Ready to auto-click.")
        except TimeoutException:
            log("CALL button not found. Exiting.")
            safe_quit(driver)
            return

        # Auto-click loop: every 10 seconds, max 10 clicks
        click_count = 0
        max_clicks = 10
        interval_seconds = 10

        while click_count < max_clicks:
            try:
                ActionChains(driver).move_to_element(call_button).click().perform()
                click_count += 1
                log(f"CALL clicked ({click_count}/{max_clicks})")
                if click_count < max_clicks:
                    time.sleep(interval_seconds)
            except WebDriverException as e:
                log(f"CALL click failed: {e}")
                time.sleep(5)

        log("Max clicks reached. Exiting.")

    except Exception as e:
        log(f"Unexpected error: {e}")
    finally:
        safe_quit(driver)

if __name__ == "__main__":
    main()
    
