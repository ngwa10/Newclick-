# core.py
"""
Core logic for Pocket Option Telegram Trading Bot.
Includes: main bot orchestrator, trade manager, Telegram listener, hotkey control, and trade execution logic.
"""

import os
import sys
import time
import traceback
import threading
import logging
import signal
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Optional, Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configure logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Health check server for Zeabur monitoring
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/health', '/', '/status']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = '{"status": "healthy", "bot": "running", "timestamp": "' + str(time.time()) + '"}'
            self.wfile.write(response.encode())
        elif self.path == '/vnc.html':
            # Redirect to noVNC if available
            self.send_response(302)
            self.send_header('Location', '/vnc_lite.html')
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress HTTP server access logs to reduce noise
        pass

def start_health_server():
    """Start health check server for Zeabur monitoring"""
    try:
        port = int(os.environ.get('PORT', 6080))
        logger.info(f"Starting health server on port {port}")
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        server.serve_forever()
    except Exception as e:
        logger.error(f"Health server failed to start: {e}")

# Optional GUI automation / OCR libraries
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
    logger.info("pyautogui loaded successfully")
except Exception as e:
    pyautogui = None
    logger.warning(f"pyautogui not available: {e}")

try:
    import pytesseract
    logger.info("pytesseract loaded successfully")
except Exception as e:
    pytesseract = None
    logger.warning(f"pytesseract not available: {e}")

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import WebDriverException
    logger.info("Selenium imports successful")
except Exception as e:
    logger.error(f"Selenium import failed: {e}")
    sys.exit(1)

# Configure line buffering for better logging
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

logger.info("[🟢] core.py starting...")

# --- Load environment variables ---
ENV_PATH = ".env"
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
    logger.info(f"[🟢] Loaded environment variables from {ENV_PATH}")
else:
    logger.warning(f"[⚠️] .env file not found at {ENV_PATH} — falling back to environment variables")

# Pocket Option credentials
EMAIL = os.getenv("POCKET_EMAIL")
PASSWORD = os.getenv("POCKET_PASS")
try:
    POST_LOGIN_WAIT = int(os.getenv("POST_LOGIN_WAIT", "180"))
except ValueError:
    POST_LOGIN_WAIT = 180

if not EMAIL or not PASSWORD:
    logger.warning("[⚠️] Pocket Option credentials not set in environment variables.")

# Telegram environment variables
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL")

if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL]):
    logger.warning("[⚠️] Missing Telegram environment variables. Telegram listener may not start.")

# Local import for Telegram integration
try:
    from telegram_integration import start_telegram_listener, parse_signal  # type: ignore
    logger.info("Telegram integration module loaded")
except Exception as e:
    start_telegram_listener = None
    parse_signal = None
    logger.warning(f"[⚠️] telegram_integration module not found: {e}")

# --- Display/Xvfb Setup ---
os.environ.setdefault('DISPLAY', ':1')
os.environ.setdefault('XAUTHORITY', '/tmp/.Xauthority')
if not os.path.exists('/tmp/.Xauthority'):
    try:
        open('/tmp/.Xauthority', 'a').close()
        logger.info("[✅] Created /tmp/.Xauthority file")
    except Exception as e:
        logger.error(f"Failed to create .Xauthority: {e}")

# -------------------------------------------------------
# Setup Chrome WebDriver with optimizations
# -------------------------------------------------------
def setup_driver(chromedriver_path: str = "/usr/bin/chromedriver", headless: bool = False,
                 user_data_dir: str = "/tmp/chrome-user-data") -> Optional[webdriver.Chrome]:
    """Setup Chrome WebDriver with containerized environment optimizations"""
    chrome_options = Options()
    
    # Essential Chrome arguments for containerized environments
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Memory optimization arguments
    chrome_options.add_argument("--memory-pressure-off")
    chrome_options.add_argument("--max_old_space_size=2048")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-client-side-phishing-detection")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    
    # Window and display settings
    chrome_options.add_argument("--window-size=1280,720")
    display = os.environ.get('DISPLAY', ':1')
    chrome_options.add_argument(f"--display={display}")
    
    # Remote debugging for troubleshooting
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    if headless:
        chrome_options.add_argument("--headless=new")
    
    logger.info(f"Chrome configured for display: {display}")

    service = Service(chromedriver_path)
    
    for attempt in range(3):
        try:
            logger.info(f"WebDriver setup attempt {attempt + 1}/3")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get("https://pocketoption.com/en/login/")
            logger.info("[✅] Chrome started and navigated to login page.")
            
            if EMAIL and PASSWORD:
                try:
                    time.sleep(2)
                    email_input = driver.find_element(By.NAME, "email")
                    password_input = driver.find_element(By.NAME, "password")
                    email_input.clear()
                    email_input.send_keys(EMAIL)
                    password_input.clear()
                    password_input.send_keys(PASSWORD)
                    logger.info(f"[🚨] Credentials entered. Waiting {POST_LOGIN_WAIT} seconds for manual login / CAPTCHA")
                    time.sleep(POST_LOGIN_WAIT)
                except Exception as e:
                    logger.warning(f"[⚠️] Could not autofill credentials: {e}")
            return driver
            
        except WebDriverException as e:
            logger.error(f"[❌] WebDriver attempt {attempt+1} failed: {e}")
            if attempt < 2:  # Don't sleep on last attempt
                time.sleep(5)
    
    logger.error("All WebDriver setup attempts failed")
    return None

# -------------------------------------------------------
# Trade Manager Class
# -------------------------------------------------------
class TradeManager:
    """Manages trading operations and signal handling"""
    
    def __init__(self, driver: Optional[webdriver.Chrome] = None, base_amount: float = 1.0, max_martingale: int = 2):
        self.trading_active = False
        self.driver = driver
        self.base_amount = base_amount
        self.max_martingale = max_martingale
        logger.info(f"TradeManager initialized - base_amount: {base_amount}, max_martingale: {max_martingale}")

    def wait_until(self, entry_time_str: str):
        """Helper to wait until a specific entry time"""
        try:
            entry_time = datetime.fromisoformat(entry_time_str).replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delay = (entry_time - now).total_seconds()
            if delay > 0:
                logger.info(f"[⏰] Waiting {delay:.2f} seconds until trade entry time")
                time.sleep(delay)
            else:
                logger.warning(f"[⚠️] Entry time {entry_time_str} is in the past")
        except Exception as e:
            logger.error(f"[⚠️] Invalid entry_time format '{entry_time_str}': {e}")

    def handle_signal(self, signal: Dict[str, Any]):
        """Handle incoming trading signal"""
        if not self.trading_active:
            logger.info("[⏸️] Trading paused. Signal ignored.")
            return

        logger.info(f"[📡] Processing signal: {signal}")

        # Schedule direct trade at entry_time
        entry_time = signal.get("entry_time")
        if entry_time:
            self.schedule_trade(entry_time, signal.get("direction", "BUY"), self.base_amount, 0)
        else:
            logger.warning("[⚠️] Signal missing entry_time, skipping direct trade")

        # Schedule martingale trades
        martingale_times = signal.get("martingale_times", []) or []
        for i, mg_time in enumerate(martingale_times):
            if i + 1 > self.max_martingale:
                logger.warning(f"[⚠️] Martingale level {i+1} exceeds max {self.max_martingale}; skipping.")
                break
            mg_amount = self.base_amount * (2 ** (i + 1))
            self.schedule_trade(mg_time, signal.get("direction", "BUY"), mg_amount, i + 1)

    def handle_command(self, command: str):
        """Handle bot commands"""
        cmd = command.strip().lower()
        if cmd.startswith("/start"):
            self.trading_active = True
            logger.info("[🚀] Trading started by user command.")
        elif cmd.startswith("/stop"):
            self.trading_active = False
            logger.info("[⏹️] Trading stopped by user command.")
        elif cmd.startswith("/status"):
            status = "ACTIVE" if self.trading_active else "PAUSED"
            logger.info(f"[ℹ️] Trading status: {status}")
        else:
            logger.info(f"[ℹ️] Unknown command: {command}")

    def schedule_trade(self, entry_time: str, direction: str, amount: float, martingale_level: int):
        """Schedule trade to run at exact entry time"""
        logger.info(f"[⚡] Scheduling trade at {entry_time} | {direction} | amount: {amount} | level: {martingale_level}")
        
        def execute_trade():
            self.wait_until(entry_time)
            self.place_trade(amount, direction)
        
        # Execute trade in separate thread to avoid blocking
        trade_thread = threading.Thread(target=execute_trade, daemon=True)
        trade_thread.start()

    def place_trade(self, amount: float, direction: str = "BUY"):
        """Execute the actual trade"""
        logger.info(f"[🎯] Placing trade: {direction} | amount: {amount}")
        
        if pyautogui is None:
            logger.warning("[⚠️] pyautogui not available; implement Selenium click fallback.")
            # TODO: Implement Selenium-based clicking as fallback
            return
        
        try:
            direction_upper = direction.upper()
            if direction_upper == "BUY":
                pyautogui.keyDown('shift')
                pyautogui.press('w')
                pyautogui.keyUp('shift')
            elif direction_upper == "SELL":
                pyautogui.keyDown('shift')
                pyautogui.press('s')
                pyautogui.keyUp('shift')
            else:
                logger.warning(f"[⚠️] Unknown direction '{direction}'. Use BUY/SELL.")
                return
            
            logger.info(f"[✅] Trade hotkey sent: {direction} | amount: {amount}")
        except Exception as e:
            logger.error(f"[❌] Error sending trade hotkeys: {e}")
            traceback.print_exc()

# -------------------------------------------------------
# Signal handlers for graceful shutdown
# -------------------------------------------------------
def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        # Add any cleanup code here if needed
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

# -------------------------------------------------------
# Main Entry Point
# -------------------------------------------------------
def main():
    """Main bot entry point"""
    logger.info("[🚀] Starting Pocket Option Trading Bot...")
    
    # Setup signal handlers for graceful shutdown
    setup_signal_handlers()
    
    # Start health check server in background thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    logger.info("[✅] Health check server started")
    
    # Wait a moment for services to stabilize
    time.sleep(5)
    
    # Setup WebDriver
    logger.info("[🌐] Setting up WebDriver...")
    driver = setup_driver()
    if not driver:
        logger.error("[❌] Failed to setup WebDriver. Bot cannot continue.")
        return 1
    
    # Initialize trade manager
    trade_manager = TradeManager(driver)
    logger.info("[✅] Trade manager initialized")

    # Start Telegram listener if available
    if start_telegram_listener:
        try:
            logger.info("[📡] Starting Telegram listener...")
            telegram_thread = threading.Thread(
                target=start_telegram_listener,
                args=(trade_manager.handle_signal, trade_manager.handle_command),
                daemon=True
            )
            telegram_thread.start()
            logger.info("[🟢] Telegram listener started.")
        except Exception as e:
            logger.error(f"[❌] Telegram listener failed: {e}")
            traceback.print_exc()
    else:
        logger.warning("[⚠️] Telegram listener not available; skipping.")

    logger.info("[🟢] Bot started! Waiting for signals...")
    logger.info("[ℹ️] Send /start command to activate trading")
    logger.info("[ℹ️] Send /stop command to pause trading")
    logger.info("[ℹ️] Bot health endpoint available at /health")
    
    try:
        # Main bot loop
        while True:
            time.sleep(30)  # Fixed: Added missing closing parenthesis
            logger.info("[💓] Bot heartbeat - still running...")
            
            # Optional: Add periodic health checks here
            try:
                if driver and driver.current_url:
                    pass  # Driver is responsive
            except Exception as e:
                logger.warning(f"[⚠️] WebDriver health check failed: {e}")
                
    except KeyboardInterrupt:
        logger.info("[🛑] Bot stopped by user (Ctrl+C).")
    except Exception as e:
        logger.error(f"[❌] Unexpected error in main loop: {e}")
        traceback.print_exc()
    finally:
        # Cleanup
        logger.info("[🧹] Cleaning up...")
        if driver:
            try:
                driver.quit()
                logger.info("[🧹] WebDriver closed.")
            except Exception as e:
                logger.warning(f"WebDriver cleanup failed: {e}")
        
        logger.info("[👋] Bot shutdown complete")

if __name__ == "__main__":
    try:
        # Check if running in test mode
        test_mode = len(sys.argv) > 1 and sys.argv[1].upper() == 'T'
        if test_mode:
            logger.info("[🧪] Running in TEST mode")
        
        exit_code = main()
        sys.exit(exit_code or 0)
    except Exception as e:
        logger.error(f"[💥] Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
