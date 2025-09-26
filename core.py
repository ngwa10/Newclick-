# CREATE

"""
Core logic for Pocket Option Telegram Trading Bot.
Includes: main bot orchestrator, trade manager, hotkey control, result detection.
"""

import time
from selenium_integration import setup_driver, select_currency_pair, select_timeframe
from telegram_integration import start_telegram_listener, parse_signal
import pyautogui
import pytesseract

class TradeManager:
    def __init__(self, driver):
        self.trading_active = False
        self.martingale_level = 0
        self.base_amount = 1  # TODO: Load from config or env
        self.max_martingale = 2  # Default to 2 for Anna signals
        self.driver = driver

    def handle_signal(self, signal):
        if not self.trading_active:
            print("[⏸️] Trading paused. Signal ignored.")
            return

        select_currency_pair(self.driver, signal['currency_pair'])
        select_timeframe(self.driver, signal['timeframe'])
        print(f"[⚡] Ready for trade: {signal}")

        self.schedule_trade(signal['entry_time'], signal['direction'], self.base_amount, martingale_level=0)
        for i, mg_time in enumerate(signal['martingale_times']):
            self.schedule_trade(mg_time, signal['direction'], self.base_amount * (2 ** (i+1)), martingale_level=i+1)

    def handle_command(self, command):
        if command.startswith("/start"):
            self.trading_active = True
            print("[🚀] Trading started by user command.")
        elif command.startswith("/stop"):
            self.trading_active = False
            print("[⏹️] Trading stopped by user command.")

    def schedule_trade(self, entry_time, direction, amount, martingale_level):
        print(f"[⏰] Scheduling trade at {entry_time} | {direction} | amount: {amount} | level: {martingale_level}")
        # TODO: Parse entry_time, wait until entry_time, then call place_trade
        # After placing trade, schedule result checking with fast_trade_result_detection

    def post_trade(self, trade_result, amount, martingale_level):
        if trade_result == "win":
            print("[✅] Trade won. Resetting martingale.")
            self.martingale_level = 0
            self.reset_trade_amount()
        elif trade_result == "loss":
            if martingale_level < self.max_martingale:
                self.martingale_level += 1
                print("[🔁] Scheduling martingale trade...")
                # TODO: Schedule next martingale trade
            else:
                print("[🛑] Max martingale reached. Resetting.")
                self.reset_trade_amount()
        else:
            print("[❓] Unknown result. Retrying detection.")

    def place_trade(self, amount=None, direction="BUY"):
        # Hotkey automation
        if amount:
            # TODO: Increase trade amount via hotkey
            pass
        if direction.upper() == "BUY":
            pyautogui.keyDown('shift'); pyautogui.press('w'); pyautogui.keyUp('shift')
        elif direction.upper() == "SELL":
            pyautogui.keyDown('shift'); pyautogui.press('s'); pyautogui.keyUp('shift')
        print(f"[🎯] Trade placed: {direction} | amount: {amount}")

    def reset_trade_amount(self):
        # TODO: Send hotkeys to decrease amount back to base
        print("[🔄] Reset trade amount to base.")

    def detect_trade_result_ocr(self, region=None):
        image = pyautogui.screenshot(region=region)
        text = pytesseract.image_to_string(image).lower()
        if "win" in text or "+$" in text:
            return "win"
        elif "loss" in text or "-$" in text:
            return "loss"
        return None

    def fast_trade_result_detection(self, ocr_region=None, timeout=10, poll_interval=1):
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.detect_trade_result_ocr(region=ocr_region)
            if result:
                return result
            time.sleep(poll_interval)
        return None

def main():
    driver = setup_driver()
    trade_manager = TradeManager(driver)
    start_telegram_listener(trade_manager.handle_signal, trade_manager.handle_command)
    print("[🟢] Bot started! Waiting for signals...")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("[🛑] Bot stopped by user.")

if __name__ == "__main__":
    main()
