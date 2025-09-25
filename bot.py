import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

SSID_FILE = "/app/ssid.txt"

def save_ssid(ssid):
    with open(SSID_FILE, "w") as f:
        f.write(ssid)
    print(f"[✅] SSID captured and saved to {SSID_FILE}")

def get_ssid_from_cookies(driver):
    cookies = driver.get_cookies()
    for cookie in cookies:
        if cookie.get("name") == "ssid":
            return cookie.get("value")
    return None

def main():
    print("[🚀] Bot started. Waiting for Pocket Option login...")

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless")  # optional: remove this if you want a visible browser
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    driver.get("https://pocketoption.com/en/login/")

    ssid_captured = False

    # Keep checking for SSID every 10 seconds
    while True:
        try:
            current_url = driver.current_url

            # ✅ Detect if user is on dashboard (cabinet page)
            if "cabinet" in current_url or "dashboard" in current_url:
                print("[🔎] Dashboard detected! Trying to capture SSID...")

                ssid = get_ssid_from_cookies(driver)
                if ssid:
                    save_ssid(ssid)
                    ssid_captured = True
                else:
                    print("[⚠️] Dashboard detected but SSID not yet available. Retrying...")

            else:
                print("[⏳] Still on login page. Waiting for manual login...")

        except Exception as e:
            print(f"[❌] Error checking SSID: {e}")

        if ssid_captured:
            print("[✅] SSID successfully captured. Bot will continue to monitor for changes...")
        
        time.sleep(10)  # check every 10 seconds

if __name__ == "__main__":
    main()
                
