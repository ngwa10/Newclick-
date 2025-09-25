import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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
    print("[🚀] Bot started. Waiting for SSID to appear in cookies...")

    # Chrome options
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    driver.get("https://pocketoption.com/en/login/")

    ssid_captured = False

    while True:
        try:
            ssid = get_ssid_from_cookies(driver)
            if ssid:
                if not ssid_captured:
                    save_ssid(ssid)
                    ssid_captured = True
                    print("[✅] SSID successfully captured. Monitoring for changes...")
                else:
                    print("[ℹ️] SSID already captured. No changes detected.")
            else:
                print("[⏳] No SSID cookie found yet. Retrying...")

        except Exception as e:
            print(f"[❌] Error checking cookies: {e}")

        time.sleep(10)  # check every 10 seconds

if __name__ == "__main__":
    main()
    
