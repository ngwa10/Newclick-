import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import os

# -----------------------
# Chrome options for headless/Xvfb environment
# -----------------------
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# Use virtual display from environment (DISPLAY=:1)
display_env = os.environ.get("DISPLAY", ":1")
chrome_options.add_argument(f"--display={display_env}")

# -----------------------
# Initialize WebDriver
# -----------------------
driver = webdriver.Chrome(options=chrome_options)
driver.get("https://pocketoption.com/en/login/")

print("[ℹ️] Waiting for manual login or cookie-based auto-login...")
time.sleep(300)  # 5 minutes to log in manually

# -----------------------
# Focus the page to send hotkeys
# -----------------------
try:
    body = driver.find_element("tag name", "body")
    body.click()
except Exception as e:
    print(f"[❌] Error focusing page body: {e}")

actions = ActionChains(driver)

# -----------------------
# Helper function for hotkeys
# -----------------------
def press_shift_key(key):
    """Press a Shift + key combination"""
    try:
        actions.key_down(Keys.SHIFT).send_keys(key).key_up(Keys.SHIFT).perform()
        print(f"[✅] Pressed Shift + {key}")
        time.sleep(1)  # small delay to ensure PocketOption registers the input
    except Exception as e:
        print(f"[❌] Error pressing Shift + {key}: {e}")

# -----------------------
# Main trading loop
# -----------------------
print("[🚀] Starting automated hotkey trading loop...")

while True:
    try:
        print("[ℹ️] Bot status: Running...")

        # 1️⃣ Increase trade amount
        press_shift_key('d')

        # 2️⃣ Buy trade
        press_shift_key('w')

        # 3️⃣ Switch to next favorite asset
        press_shift_key(Keys.TAB)

        # Wait 10 seconds before next cycle
        time.sleep(10)

    except Exception as e:
        print(f"[❌] Error in trading loop: {e}")
        time.sleep(5)
                         
