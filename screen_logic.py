import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# -------------------------
# Hardcoded email (from your existing code)
# -------------------------
EMAIL = "your_email_here"  # replace with the actual email from your code

# -------------------------
# Chrome options
# -------------------------
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")  # attach to existing Chrome
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-dev-shm-usage")

# -------------------------
# Connect to running Chrome
# -------------------------
service = Service("/usr/local/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)

# -------------------------
# Navigate to login page (if not already there)
# -------------------------
driver.get("http://pocketoption.com/en/login/")
time.sleep(5)  # wait for page to fully load

# -------------------------
# Fill email field only
# -------------------------
try:
    email_input = driver.find_element(By.NAME, "email")  # adjust selector if different
    email_input.clear()
    email_input.send_keys(EMAIL)
    print("[✅] Email field filled successfully.")
except Exception as e:
    print(f"[⚠️] Failed to fill email field: {e}")

# -------------------------
# Do NOT click login
# -------------------------
# driver.find_element(...).click()  # intentionally left out

# Keep the script alive briefly to ensure changes persist
time.sleep(3)
driver.quit()
