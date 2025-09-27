"""
Core logic for Pocket Option Telegram Trading Bot.
Handles Telegram signals, currency selection, trade execution via hotkeys,
martingale logic, and OTC time conversion.
"""

import os
import sys
import time
import threading
import logging
import signal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import pyautogui

# =========================
# HARD-CODED CREDENTIALS
# =========================
EMAIL = "mylivemyfuture@123gmail.com"
PASSWORD = "AaCcWw3468,"

# Telegram credentials
TELEGRAM_API_ID = 29630724
TELEGRAM_API_HASH = "8e12421a95fd722246e0c0b194fd3e0c"
TELEGRAM_BOT_TOKEN = "8477806088:AAGEXpIAwN5tNQM0hsCGqP-otpLJjPJLmWA"
TELEGRAM_CHANNEL = "-1003033183667"

# Trading settings
BASE_AMOUNT = 1.0
MAX_MARTINGALE = 2
CURRENCY_SWITCH_DELAY = 5  # seconds between Shift+TAB presses
OTC_DIFF_HOURS = 1  # adjust OTC-4 to OTC-3

# =========================
# Logging Setup
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# =========================
# Trade Manager
# =========================
class TradeManager:
    def __init__(self):
        self.trading_active = True
        self.current_martingale = 0
        self.last_currency = None
        self.lock = threading.Lock()

    def handle_signal(self, signal: Dict[str, Any]):
        if not self.trading_active:
            return

        currency_pair = signal.get("currency_pair")
        direction = signal.get("direction", "BUY")
        entry_time = signal.get("entry_time")
        martingale_times = signal.get("martingale_times", [])

        if entry_time:
            # Convert OTC-4 to OTC-3 if needed
            entry_time_dt = self.convert_otc_time(entry_time, signal.get("otc", "-3"))
            threading.Thread(target=self.execute_trade_flow, args=(currency_pair, direction, entry_time_dt, martingale_times), daemon=True).start()

    def convert_otc_time(self, entry_time_str: str, otc_signal: str):
        fmt = "%H:%M:%S" if len(entry_time_str) == 8 else "%H:%M"
        entry_dt = datetime.strptime(entry_time_str, fmt)
        if otc_signal == "-4":
            entry_dt += timedelta(hours=OTC_DIFF_HOURS)
        # Make entry_dt timezone-aware (UTC)
        return entry_dt.replace(tzinfo=timezone.utc)

    def execute_trade_flow(self, currency_pair, direction, entry_time_dt, martingale_times):
        # 1️⃣ Cycle currency pairs until correct one is selected
        self.select_currency_pair(currency_pair)

        # 2️⃣ Wait until entry time
        self.wait_until(entry_time_dt)

        # 3️⃣ Place first trade
        self.place_trade(direction, BASE_AMOUNT)
        self.current_martingale = 0

        # 4️⃣ Schedule martingale trades
        for i, mg_time_str in enumerate(martingale_times):
            if i + 1 > MAX_MARTINGALE:
                break
            mg_dt = self.convert_otc_time(mg_time_str, "-3")  # assume all MG times in same time zone
            mg_amount = BASE_AMOUNT * (2 ** (i + 1))
            threading.Thread(target=self.wait_and_trade, args=(mg_dt, direction, mg_amount, i+1), daemon=True).start()

    def wait_and_trade(self, entry_time, direction, amount, mg_level):
        self.wait_until(entry_time)
        self.place_trade(direction, amount)
        with self.lock:
            self.current_martingale = mg_level

    def wait_until(self, entry_time):
        now = datetime.now(timezone.utc)
        delay = (entry_time - now).total_seconds()
        if delay > 0:
            time.sleep(delay)

    def place_trade(self, direction, amount):
        try:
            # For BUY / SELL
            if direction.upper() == "BUY":
                pyautogui.keyDown('shift')
                pyautogui.press('w')
                pyautogui.keyUp('shift')
            elif direction.upper() == "SELL":
                pyautogui.keyDown('shift')
                pyautogui.press('s')
                pyautogui.keyUp('shift')
            logger.info(f"[💸] Trade placed: {direction} | Amount: {amount}")
        except Exception as e:
            logger.error(f"[❌] Failed to place trade: {e}")

    def select_currency_pair(self, target_currency):
        logger.info(f"[🧭] Selecting currency pair: {target_currency}")
        attempts = 0
        while True:
            current_currency = self.detect_current_currency()
            if current_currency == target_currency:
                logger.info(f"[✅] Currency selected: {current_currency}")
                break
            pyautogui.keyDown('shift')
            pyautogui.press('tab')  # Switch to next favorite asset
            pyautogui.keyUp('shift')
            attempts += 1
            if attempts > 50:  # safety max attempts
                logger.warning("[⚠️] Max currency switch attempts reached")
                break
            time.sleep(CURRENCY_SWITCH_DELAY)

    def detect_current_currency(self):
        # TODO: Implement detection logic (via Selenium or OCR)
        # For now we assume pyautogui screenshot + OCR or manual verification
        return self.last_currency or "USD/JPY"  # placeholder

    def handle_command(self, command: str):
        cmd = command.strip().lower()
        if cmd.startswith("/start"):
            self.trading_active = True
        elif cmd.startswith("/stop"):
            self.trading_active = False

# =========================
# Main
# =========================
def main():
    from telegram_integration import start_telegram_listener
    trade_manager = TradeManager()
    threading.Thread(
        target=start_telegram_listener,
        args=(trade_manager.handle_signal, trade_manager.handle_command),
        daemon=True
    ).start()

    while True:
        time.sleep(30)

if __name__ == "__main__":
    main()
        
