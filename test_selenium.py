from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# --------------------------
# Credentials (replace if needed)
# --------------------------
EMAIL = "mylivemyfuture@123gmail.com"
PASSWORD = "AaCcWw3468,"

# --------------------------
# Chrome options
# --------------------------
options = Options()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--start-maximized")
options.add_argument("--user-data-dir=/tmp/chrome-user-data")
# options.add_argument("--headless=new")  # optional: comment out if you want VNC visible

# --------------------------
# Start Chrome
# --------------------------
service = Service("/usr/local/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

try:
    # --------------------------
    # Navigate to Pocket Option login
    # --------------------------
    driver.get("https://pocketoption.com/en/login/")

    # --------------------------
    # Wait for login fields to appear
    # --------------------------
    wait = WebDriverWait(driver, 15)
    email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
    password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))

    # --------------------------
    # Auto-fill credentials
    # --------------------------
    email_input.clear()
    email_input.send_keys(EMAIL)

    password_input.clear()
    password_input.send_keys(PASSWORD)

    # Optional: click login button
    login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
    login_button.click()

    print("[✅] Auto-login completed successfully!")

    # Keep browser open a bit for verification
    time.sleep(10)

except Exception as e:
    print(f"[❌] Auto-login failed: {e}")
    raise

finally:
    driver.quit()
  
