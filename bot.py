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
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def init_driver(retries=3):
    """Initialize ChromeDriver with retries."""
    for attempt in range(1, retries + 1):
        try:
            log(f"Initializing ChromeDriver (attempt {attempt})...")
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--headless=new")  # headless mode
            chrome_options.add_argument("--verbose")
            chrome_options.add_argument("--log-path=/app/chromedriver.log")

            driver = webdriver.Chrome(options=chrome_options)
            log("ChromeDriver initialized successfully.")
            return driver
        except Exception as e:
            log(f"ChromeDriver init failed (attempt {attempt}): {e}")
            time.sleep(5)
    log("ChromeDriver could not be initialized.")
    return None


def safe_quit(driver):
    """Quit driver safely."""
    try:
        if driver:
            driver.quit()
            log("Driver quit successfully.")
    except Exception as e:
        log(f"Error quitting driver: {e}")


def fill_login_form(driver):
    """Fill in login credentials but do not submit."""
    try:
        log("Filling login form with credentials from .env...")
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        password_field = driver.find_element(By.NAME, "password")
        email_field.clear()
        email_field.send_keys(PO_EMAIL)
        password_field.clear()
        password_field.send_keys(PO_PASS)
        log("Credentials typed. Please click LOGIN manually to continue.")
    except Exception as e:
        log(f"Failed to fill login form: {e}")


def wait_for_manual_login(driver, timeout=600):
    """Wait until cabinet/dashboard page is detected."""
    log("Waiting for manual login (detecting cabinet page)...")
    try:
        wait = WebDriverWait(driver, timeout)
        # Multiple possible selectors for dashboard elements
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.cabinet-container, div.account-info, header.dashboard-header")
        ))
        log("Manual login detected: cabinet page loaded!")
        return True
    except TimeoutException:
        log("Manual login not detected within timeout.")
        return False
    except Exception as e:
        log(f"Error while waiting for manual login: {e}")
        return False


def capture_ssid(driver):
    """Read SSID cookie and save it to a file."""
    cookies = driver.get_cookies()
    ssid = None
    for c in cookies:
        if c['name'] == 'ssid':
            ssid = c['value']
            break
    if ssid:
        log(f"SSID captured: {ssid}")
        with open("/app/ssid.txt", "w") as f:
            f.write(ssid)
        log("SSID saved to /app/ssid.txt")
    else:
        log("SSID not found.")


def main():
    log("Bot starting...")
    driver = init_driver()
    if not driver:
        log("Exiting: driver not initialized.")
        return

    try:
        log("Opening login page...")
        driver.get("https://pocketoption.com/en/login/")
        fill_login_form(driver)

        if not wait_for_manual_login(driver):
            log("Exiting: manual login not detected.")
            safe_quit(driver)
            return

        log("Manual login complete. Capturing SSID...")
        capture_ssid(driver)

        log("SSID capture complete. Exiting bot.")
    except Exception as e:
        log(f"Unexpected error: {e}")
    finally:
        safe_quit(driver)


if __name__ == "__main__":
    main()
            
