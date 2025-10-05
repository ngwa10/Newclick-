"""
selenium_integration.py — PocketOptionSelenium (refactor)

Notes:
- Implements select_asset: open currency dropdown -> search -> paste currency -> click top result.
- prepare_for_trade returns boolean and launches monitor threads that attempt to attribute result to asset.
- detect_trade_result_structured returns list of dicts like {'asset': 'EURUSD', 'result': 'WIN', 'raw_text': '...'}
- start_result_monitor reduces misattribution by matching asset names.
- Keeps login, screenshot on login, captcha handling as before (best-effort).
"""

import time
import threading
import random
import uuid
import logging
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import pyautogui

logger = logging.getLogger(__name__)

# Hardcoded credentials (deployment) — consider moving to env vars
EMAIL = "mylivemyfuture@123gmail.com"
PASSWORD = "AaCcWw3468,"

CHECK_INTERVAL = 0.5  # regular scan interval (s)
INTENSE_POLL_INTERVAL = 0.1  # intensive poll interval (s)
MONITOR_LEAD_SECONDS = 30  # seconds before expected result to start intensive monitoring

pyautogui.FAILSAFE = False

# timeframe seconds mapping
TIMEFRAME_SECONDS = {
    "M1": 60,
    "M5": 300
}

if not EMAIL or not PASSWORD:
    raise ValueError("EMAIL or PASSWORD not set.")

class PocketOptionSelenium:
    def __init__(self, trade_manager, headless=True, hotkey_mode=True, chromedriver_path="/usr/local/bin/chromedriver"):
        self.trade_manager = trade_manager
        self.headless = headless
        self.hotkey_mode = hotkey_mode
        self.driver = self.setup_driver(headless, chromedriver_path)
        self._monitors = {}           # key: (currency, entry_iso) -> monitor info
        self._monitors_lock = threading.RLock()
        self._global_monitor_running = False
        self.start_result_monitor()
        logger.info("[🟢] Selenium initialized and ready — waiting for orders from Core.")

    # -----------------
    # Setup Chrome
    # -----------------
    def setup_driver(self, headless=True, chromedriver_path="/usr/local/bin/chromedriver"):
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--start-maximized")

        session_id = str(uuid.uuid4())
        chrome_options.add_argument(f"--user-data-dir=/tmp/chrome-user-data-{session_id}")

        # headless handling: optional, may need Xvfb when using pyautogui
        if headless:
            try:
                chrome_options.add_argument("--headless=new")
            except Exception:
                chrome_options.add_argument("--headless")

        try:
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get("https://pocketoption.com/en/login/")
            logger.info("[✅] Chrome started and navigated to login.")
        except Exception as e:
            logger.exception(f"[❌] Could not start Chrome/Chromedriver: {e}")
            raise

        # Auto-login (best-effort)
        try:
            wait = WebDriverWait(driver, 20)
            email_field = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
            email_field.clear()
            email_field.send_keys(EMAIL)
            password_field.clear()
            password_field.send_keys(PASSWORD)
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            logger.info("[🔐] Login submitted.")
            # capture screenshot on login (helpful for debugging captcha)
            time.sleep(2)
            try:
                driver.save_screenshot("login_screenshot.png")
                logger.info("[📷] Captured login screenshot login_screenshot.png")
            except Exception:
                pass
            # allow possible captcha manual intervention (if running with VNC)
            time.sleep(3)
        except Exception as e:
            logger.warning(f"[⚠️] Auto-login failed or missing fields: {e}")

        return driver

    # -----------------
    # Utility: small randomized pause (2-10s)
    # -----------------
    def _rand_pause(self, a=2.0, b=10.0):
        s = random.uniform(a, b)
        logger.debug(f"[⌛] Waiting {s:.1f}s (randomized pause).")
        time.sleep(s)

    # -----------------
    # Select asset: opens dropdown, types pair (no slash), clicks first result (prefer OTC)
    # -----------------
    def select_asset(self, currency_pair: str, max_attempts: int = 3) -> bool:
        """
        Clicks the currency dropdown, finds the search input, types the pair and clicks the first returned result.
        Returns True on success, False on failure.
        """
        normalized_pair = currency_pair.replace("/", "").replace(" ", "").upper()
        logger.info(f"[🔎] select_asset called for '{currency_pair}' -> normalized '{normalized_pair}'")
        try:
            wait = WebDriverWait(self.driver, 8)

            # 1) Click/open the asset dropdown - try multiple selectors
            dropdown_selectors = [
                ("css", "button.asset-selector"),
                ("css", "div.asset-name-selector"),
                ("css", ".asset-dropdown-opener"),
                ("xpath", "//button[contains(@class,'asset') and (contains(., 'Assets') or contains(., 'Select'))]"),
                ("css", ".header-asset-selector"),
            ]
            opened = False
            for kind, sel in dropdown_selectors:
                try:
                    if kind == "css":
                        elem = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                    else:
                        elem = wait.until(EC.element_to_be_clickable((By.XPATH, sel)))
                    elem.click()
                    opened = True
                    logger.debug(f"[🖱️] Clicked dropdown using selector {sel}")
                    break
                except Exception:
                    continue
            if not opened:
                logger.warning("[⚠️] Could not open asset dropdown.")
                return False

            # 2) Find the search input inside the dropdown
            try:
                search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.asset-search, input[placeholder*='Search'], input[type='search']")))
            except Exception:
                # fallback XPath
                try:
                    search_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[contains(@class,'search') or contains(@placeholder,'Search')]")))
                except Exception:
                    logger.warning("[⚠️] Search input not found inside asset dropdown.")
                    return False

            # 3) Type/paste the pair
            try:
                search_input.clear()
                # send as text; clipboard paste can be used as alternative
                search_input.send_keys(normalized_pair)
                time.sleep(0.2)
                logger.debug(f"[🔤] Typed into search input: {normalized_pair}")
            except Exception as e:
                logger.warning(f"[⚠️] Failed typing into search input: {e}")
                return False

            # 4) Wait for the first result (we expect it to contain the normalized_pair)
            try:
                xpath_fragment = f"contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{normalized_pair}')"
                # many sites wrap options in a div with 'asset' or 'option' class - we search broadly
                result_xpath = f"//div[{xpath_fragment} and (contains(@class,'asset') or contains(@class,'asset-item') or contains(@class,'option') or contains(@class,'list-item'))]"
                result_elem = wait.until(EC.element_to_be_clickable((By.XPATH, result_xpath)))
                txt = result_elem.text.strip().upper()
                if normalized_pair not in txt:
                    logger.debug(f"[⚠️] Top result text does not contain '{normalized_pair}': '{txt[:80]}'")
                # click result (try direct then JS fallback)
                try:
                    result_elem.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", result_elem)
                logger.info(f"[✅] select_asset succeeded for {currency_pair} (selected: {txt[:80]})")
                time.sleep(0.7)
                return True
            except Exception as e:
                logger.warning(f"[⚠️] Could not find/click the asset result for '{normalized_pair}': {e}")
                try:
                    fn = f"select_asset_fail_{normalized_pair}_{int(time.time())}.png"
                    self.driver.save_screenshot(fn)
                    logger.info(f"[ℹ️] Saved screenshot to {fn}")
                except Exception:
                    pass
                return False

        except Exception as e:
            logger.exception(f"[❌] Unexpected error in select_asset: {e}")
            return False

    # -----------------
    # Set timeframe: open dropdown, wait, pick timeframe (1M/5M)
    # -----------------
    def set_timeframe(self, timeframe="M1", max_attempts=3):
        try:
            for attempt in range(max_attempts):
                try:
                    tf_opener = WebDriverWait(self.driver, 6).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, ".timeframe-selector .current, .timeframe-selector"))
                    )
                    tf_opener.click()
                    logger.debug("[🖱️] Clicked timeframe dropdown opener.")
                    self._rand_pause()

                    options = self.driver.find_elements(By.CSS_SELECTOR, ".timeframe-selector .option, .timeframe-list .option, .timeframe-item")
                    if not options:
                        logger.debug("[⚠️] No timeframe options found; retrying...")
                        time.sleep(0.4)
                        continue

                    selected = None
                    tf_upper = timeframe.upper()
                    for opt in options:
                        txt = opt.text.strip().upper()
                        if tf_upper in txt or (tf_upper == "M1" and ("1M" in txt or "1 MIN" in txt)) or (tf_upper == "M5" and ("5M" in txt or "5 MIN" in txt)):
                            selected = opt
                            break

                    if not selected:
                        selected = options[0]

                    try:
                        selected.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", selected)

                    logger.debug(f"[🖱️] Selected timeframe option: {selected.text.strip()[:40]}")
                    self._rand_pause()
                    # small click to close
                    try:
                        width = self.driver.execute_script("return window.innerWidth")
                        height = self.driver.execute_script("return window.innerHeight")
                        x = int(width * 0.5)
                        y = int(height * 0.5)
                        pyautogui.click(x, y)
                    except Exception:
                        pass
                    return True

                except Exception as e:
                    logger.debug(f"[⚠️] set_timeframe attempt failed: {e}")
                    time.sleep(0.5)
            return False
        except Exception as e:
            logger.exception(f"[❌] set_timeframe fatal error: {e}")
            return False

    # -----------------
    # Called by Core to prepare trade UI and start monitoring for its result
    # returns True when selection finished (asset+tf) and monitor thread launched
    # -----------------
    def prepare_for_trade(self, currency_pair, entry_dt, timeframe="M1"):
        try:
            logger.info(f"[📥] Selenium received order from Core: {currency_pair} | Timeframe: {timeframe} | Entry at: {entry_dt.strftime('%H:%M:%S')}")
            sel_ok = self.select_asset(currency_pair)
            if not sel_ok:
                logger.warning(f"[⚠️] select_asset failed for {currency_pair}")
            tf_ok = self.set_timeframe(timeframe)
            if not tf_ok:
                logger.warning(f"[⚠️] set_timeframe failed for {timeframe}")

            # compute expected result time (entry -> plus timeframe seconds)
            tf_seconds = TIMEFRAME_SECONDS.get(timeframe.upper(), 60)
            expected_result_dt = entry_dt + timedelta(seconds=tf_seconds)

            key = (currency_pair.replace("/", "").replace(" ", "").upper(), entry_dt.isoformat())
            with self._monitors_lock:
                if key in self._monitors:
                    logger.debug(f"[ℹ️] Monitor already exists for {key}")
                else:
                    t = threading.Thread(target=self._monitor_for_result,
                                         args=(currency_pair, entry_dt, expected_result_dt, timeframe),
                                         daemon=True)
                    self._monitors[key] = {"thread": t, "started_at": datetime.utcnow()}
                    t.start()

            logger.info(f"[✅] Asset {currency_pair} and timeframe {timeframe} selection attempted; monitor set for result at {expected_result_dt.strftime('%H:%M:%S')}")
            return sel_ok or tf_ok
        except Exception as e:
            logger.exception(f"[❌] prepare_for_trade error: {e}")
            return False

    # -----------------
    # Internal monitor per expected result
    # -----------------
    def _monitor_for_result(self, currency_pair, entry_dt, result_dt, timeframe):
        iso_key = (currency_pair.replace("/", "").replace(" ", "").upper(), entry_dt.isoformat())
        try:
            logger.debug(f"[🔎] Monitor thread started for {currency_pair} expected result at {result_dt.isoformat()}")
            # Poll lightly until MONITOR_LEAD_SECONDS before result_dt
            while True:
                now = datetime.now(entry_dt.tzinfo)
                seconds_to_result = (result_dt - now).total_seconds()
                if seconds_to_result <= MONITOR_LEAD_SECONDS:
                    break
                time.sleep(max(0.5, min(2.0, seconds_to_result / 5.0)))
            # intensive poll window (until result_dt + small buffer)
            end_time = result_dt + timedelta(seconds=15)
            logger.info(f"[🔔] Selenium intensive monitoring started for {currency_pair} — checking every {INTENSE_POLL_INTERVAL}s until {end_time.strftime('%H:%M:%S')}")
            while datetime.now(entry_dt.tzinfo) <= end_time:
                res_list = self.detect_trade_result_structured()
                if res_list:
                    # find a matching asset result
                    for r in res_list:
                        asset = (r.get("asset") or "").replace("/", "").replace(" ", "").upper()
                        result = r.get("result")
                        if asset == currency_pair.replace("/", "").replace(" ", "").upper():
                            logger.info(f"[📤] Selenium detected trade result for {currency_pair}: {result}. Sending result to Core.")
                            try:
                                self.trade_manager.on_trade_result(currency_pair.replace("/", "").replace(" ", "").upper(), result)
                            except Exception as e:
                                logger.exception(f"[❌] Error notifying core for {currency_pair}: {e}")
                            return
                time.sleep(INTENSE_POLL_INTERVAL)
        except Exception as e:
            logger.exception(f"[❌] Monitor thread error for {currency_pair}: {e}")
        finally:
            with self._monitors_lock:
                if iso_key in self._monitors:
                    del self._monitors[iso_key]
            logger.debug(f"[🔚] Monitor thread ended for {currency_pair} entry {entry_dt.isoformat()}")

    # -----------------
    # Parse trade-results in history DOM; returns list of structured entries or None
    # -----------------
    def detect_trade_result_structured(self):
        """
        Scans the trade history for recent entries and returns a list of dicts:
        [{"asset": "EURUSD", "result": "WIN", "raw_text": "...", "timestamp_text": "..."} , ...]
        Best-effort: selectors may need tuning for the live DOM.
        """
        out = []
        try:
            # try to find rows that include asset + result
            # many sites have a trade-history section with items; search broadly
            rows = []
            try:
                rows = self.driver.find_elements(By.CSS_SELECTOR, ".trade-history .trade-row, .trade-history .trade-item, .trade-history .history-item")
            except Exception:
                pass
            if not rows:
                # broader fallback: any element that contains result-like text
                try:
                    rows = self.driver.find_elements(By.CSS_SELECTOR, ".trade-history .trade-result, .history-list .item")
                except Exception:
                    pass

            for r in rows:
                try:
                    txt = r.text.strip()
                    if not txt:
                        continue
                    # attempt to extract asset and result from the row text (heuristic)
                    # e.g., "EURUSD +$1.00 23:35" or "EUR/USD WIN 23:35"
                    asset = None
                    result = None
                    timestamp_text = None

                    # try to find child elements first
                    try:
                        asset_elem = r.find_element(By.CSS_SELECTOR, ".asset-name")
                        asset = asset_elem.text.strip()
                    except Exception:
                        # heuristic: first token of the row maybe asset
                        parts = txt.split()
                        if parts:
                            maybe = parts[0].replace("/", "").upper()
                            if len(maybe) >= 6:
                                asset = maybe

                    # find result text candidates
                    try:
                        res_elem = r.find_element(By.CSS_SELECTOR, ".trade-result")
                        raw_result = res_elem.text.strip()
                    except Exception:
                        raw_result = txt

                    rr = raw_result.strip()
                    if rr.startswith("+") or rr.lower().startswith("win") or "+" in rr:
                        result = "WIN"
                    elif rr == "$0" or rr.lower().startswith("0") or "loss" in rr.lower() or "-" in rr:
                        result = "LOSS"

                    # timestamp heuristic: try child .trade-time
                    try:
                        ts_elem = r.find_element(By.CSS_SELECTOR, ".trade-time, .time")
                        timestamp_text = ts_elem.text.strip()
                    except Exception:
                        timestamp_text = None

                    if result:
                        out.append({
                       
