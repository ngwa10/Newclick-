"""
Selenium utilities for Pocket Option:
- Detects trade results (win/loss) continuously.
- Can be integrated with core to stop martingale on win.
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

CHECK_INTERVAL = 0.5  # check every 0.5 seconds

def setup_driver(headless=False):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-data-dir=/tmp/chrome-user-data")
    if headless:
        chrome_options.add_argument("--headless=new")
    
    service = Service("/usr/local/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://pocketoption.com/en/login/")
    print("[✅] Chrome started and navigated to Pocket Option login.")
    return driver

def detect_trade_result(driver):
    """
    Continuously checks for the last trade result:
    - Win: text starts with '+' and has a green checkmark
    - Loss: text is exactly '$0' with a red cross
    Returns: "WIN", "LOSS", or None if no result yet
    """
    try:
        while True:
            # Adjust selectors based on Pocket Option UI
            # Example placeholders
            result_elements = driver.find_elements(By.CSS_SELECTOR, ".trade-history .trade-result")
            for elem in result_elements:
                text = elem.text.strip()
                # Win condition
                if text.startswith("+"):
                    return "WIN"
                # Loss condition
                elif text == "$0":
                    return "LOSS"
            time.sleep(CHECK_INTERVAL)
    except Exception as e:
        print(f"[❌] Error detecting trade result: {e}")
        return None

def start_result_monitor(driver, callback):
    """
    Starts a background thread to monitor trade results.
    Calls `callback(result)` when a WIN or LOSS is detected.
    """
    import threading
    def monitor():
        while True:
            result = detect_trade_result(driver)
            if result:
                callback(result)
            time.sleep(CHECK_INTERVAL)
    threading.Thread(target=monitor, daemon=True).start()
            
