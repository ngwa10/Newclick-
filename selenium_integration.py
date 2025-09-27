"""
Selenium functions for Pocket Option automation: setup, currency pair & timeframe selection, and trade result detection.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

# =========================
# WebDriver Setup
# =========================
def setup_driver(chromedriver_path="/usr/local/bin/chromedriver", headless=False):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--user-data-dir=/tmp/chrome-user-data")
    if headless:
        chrome_options.add_argument("--headless=new")
    
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://pocketoption.com/en/login/")
    print("[✅] Chrome started and navigated to Pocket Option login.")
    return driver

# =========================
# Currency Pair Selection
# =========================
def select_currency_pair(driver, pair_name):
    """Select a currency pair by name."""
    try:
        search_input = driver.find_element(By.XPATH, "//input[@placeholder='Search']")
        search_input.clear()
        search_input.send_keys(pair_name)
        time.sleep(0.5)
        pair_element = driver.find_element(By.XPATH, f"//div[contains(@class,'pair-item') and text()='{pair_name}']")
        pair_element.click()
        print(f"[🧭] Selected currency pair: {pair_name}")
    except NoSuchElementException:
        print(f"[⚠️] Currency pair '{pair_name}' not found.")

# =========================
# Timeframe Selection
# =========================
def select_timeframe(driver, timeframe):
    """
    Select timeframe if different from the currently selected one.
    Supported: 'M1', 'M5'
    """
    try:
        current_tf_element = driver.find_element(By.XPATH, "//div[contains(@class,'timeframe-dropdown')]")
        current_tf = current_tf_element.text.strip()
        if current_tf == timeframe:
            print(f"[⏱️] Timeframe already set to {timeframe}, no action needed.")
            return

        current_tf_element.click()
        time.sleep(0.2)
        tf_option = driver.find_element(By.XPATH, f"//div[contains(@class,'timeframe-item') and text()='{timeframe}']")
        tf_option.click()
        print(f"[⏱️] Timeframe changed to {timeframe}.")
    except NoSuchElementException:
        print(f"[⚠️] Timeframe '{timeframe}' option not found.")

# =========================
# Trade Result Detection
# =========================
def detect_trade_result(driver, check_interval=0.5):
    """
    Continuously check the latest trade result.
    Returns:
        'WIN' if last trade was a win
        'LOSS' if last trade was a loss
        None if no result yet
    """
    try:
        result_element = driver.find_element(By.XPATH, "//div[contains(@class,'last-trade-result')]")
        text = result_element.text.strip()
        if text.startswith("+$"):
            return "WIN"
        elif text == "$0":
            return "LOSS"
    except NoSuchElementException:
        return None
    time.sleep(check_interval)
    return None
    
