#!/usr/bin/env python3
"""
Bot orchestrator for Pocket Option Telegram Trading.
Manages health server, Telegram listener, trades, and GUI automation.
"""

import os
import sys
import time
import threading
import logging
import signal
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

# -------------------------
# Logging
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/bot.log")
    ]
)
logger = logging.getLogger(__name__)

# -------------------------
# Environment
# -------------------------
os.environ.setdefault("DISPLAY", ":1")

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
    pyautogui.size()  # sanity check
    logger.info("[✅] pyautogui loaded and display accessible")
except Exception as e:
    pyautogui = None
    logger.warning(f"[⚠️] pyautogui not available: {e}")

try:
    from telegram_integration import start_telegram_listener
    logger.info("[✅] Telegram module loaded")
except Exception as e:
    start_telegram_listener = None
    logger.warning(f"[⚠️] Telegram listener not available: {e}")

# -------------------------
# Trade Manager
# -------------------------
class TradeManager:
    def __init__(self, base_amount: float = 1.0, max_martingale: int = 2):
        self.trading_active = False
        self.base_amount = base_amount
        self.max_martingale = max_martingale

    def handle_command(self, command: str):
        cmd = command.strip().lower()
        if cmd.startswith("/start"):
            self.trading_active = True
        elif cmd.startswith("/stop"):
            self.trading_active = False

    def handle_signal(self, signal_data: Dict[str, Any]):
        if not self.trading_active:
            return
        # For simplicity, we just log signals
        logger.info(f"[📈] Signal received: {signal_data}")

    def place_trade(self, amount: float, direction: str):
        if pyautogui is None:
            return
        try:
            key = "w" if direction.upper() == "BUY" else "s"
            pyautogui.keyDown("shift")
            pyautogui.press(key)
            pyautogui.keyUp("shift")
            logger.info(f"[💹] Placed trade {direction} with {amount}")
        except Exception as e:
            logger.warning(f"[⚠️] Trade failed: {e}")

# -------------------------
# Health server
# -------------------------
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ["/", "/health", "/status"]:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(
                f'{{"status":"healthy","bot":"running","timestamp":{time.time()}}}'.encode()
            )
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress logs

def start_health_server():
    server = HTTPServer(("0.0.0.0", 6081), HealthHandler)
    server.serve_forever()

# -------------------------
# Signal Handlers
# -------------------------
def setup_signal_handlers():
    def handler(signum, frame):
        logger.info("[✋] Exiting...")
        sys.exit(0)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)

# -------------------------
# Main
# -------------------------
def main():
    setup_signal_handlers()
    threading.Thread(target=start_health_server, daemon=True).start()
    trade_manager = TradeManager()
    if start_telegram_listener:
        threading.Thread(
            target=start_telegram_listener,
            args=(trade_manager.handle_signal, trade_manager.handle_command),
            daemon=True
        ).start()
    while True:
        time.sleep(30)

if __name__ == "__main__":
    main()
    
