import time
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
    print("[🚀] Bot started. Waiting for Pocket Option login...")

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--headless")  # remove if you want a visible browser
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    driver.get("https://pocketoption.com/en/login/")

    while True:
        try:
            current_url = driver.current_url.lower()
            if "cabinet" in current_url or "dashboard" in current_url:
                print(f"[🔎] Dashboard detected ({current_url})! Trying to capture SSID...")
                ssid = get_ssid_from_cookies(driver)
                if ssid:
                    save_ssid(ssid)
                else:
                    print("[⚠️] Dashboard detected but SSID not yet available. Retrying...")
            else:
                print(f"[⏳] Still on login page ({current_url}). Waiting for manual login...")
        except Exception as e:
            print(f"[❌] Error checking SSID: {e}")
        time.sleep(10)

if __name__ == "__main__":
    main()
        
