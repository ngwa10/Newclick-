"""
Telegram integration: Listener and signal parser with detailed logging.
Supports Anna, Precisiontrike, and OTC signal formats.
Handles multiple timezones and prepares signals for core.py trading.
"""

from telethon import TelegramClient, events
import re
from datetime import datetime, timedelta
import logging

# =========================
# HARD-CODED CREDENTIALS
# =========================
api_id = 29630724
api_hash = "8e12421a95fd722246e0c0b194fd3e0c"
bot_token = "8477806088:AAGEXpIAwN5tNQM0hsCGqP-otpLJjPJLmWA"
TARGET_CHAT_ID = -1003033183667  # Numeric channel ID

# =========================
# Logging Setup
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)

def log_info(msg):
    logging.info(msg)
    for handler in logging.getLogger().handlers:
        handler.flush()

def log_error(msg):
    logging.error(msg)
    for handler in logging.getLogger().handlers:
        handler.flush()

# =========================
# Import core_utils for timezone conversion
# =========================
try:
    from core_utils import timezone_convert
except Exception:
    timezone_convert = None
    log_error("[⚠️] core_utils.timezone_convert not found, signals will use raw strings!")

# =========================
# Telegram Client Setup
# =========================
client = TelegramClient('bot_session', api_id, api_hash)

# =========================
# Signal Parser
# =========================
def parse_signal(message_text):
    result = {
        "currency_pair": None,
        "direction": None,
        "entry_time": None,
        "timeframe": None,
        "martingale_times": [],
        "source": "OTC-3"
    }

    try:
        if not re.search(r'(BUY|SELL|CALL|PUT|🔼|🟥|🟩|🔽|✅ ANNA SIGNALS ✅|_OTC)', message_text, re.IGNORECASE):
            return None

        is_anna_signal = "anna signals" in message_text.lower()
        clean_text = re.sub(r'[^\x00-\x7F]+', ' ', message_text)

        # Currency Pair
        pair_match = re.search(r'([A-Z]{3}/[A-Z]{3})(?:[\s_\-]?OTC)?', clean_text, re.IGNORECASE)
        if pair_match:
            result['currency_pair'] = pair_match.group(0).strip()

        # Direction
        direction_match = re.search(r'(BUY|SELL|CALL|PUT|🔼|🟥|🟩|🔽|⏺ BUY|⏺ SELL)', message_text, re.IGNORECASE)
        if direction_match:
            direction = direction_match.group(1).upper()
            if direction in ['CALL','BUY','🟩','🔼','⏺ BUY']:
                result['direction'] = 'BUY'
            elif direction in ['PUT','SELL','🔽','🟥','⏺ SELL']:
                result['direction'] = 'SELL'

        # Entry Time
        entry_time_match = re.search(r'(?:Entry Time:|Entry at|TIME \(UTC.*\):|⏺ Entry at)\s*(\d{2}:\d{2})', message_text)
        if entry_time_match:
            entry_time_str = entry_time_match.group(1)
            source = "OTC-3"
            if "💥 GET THIS SIGNAL HERE!" in message_text:
                source = "UTC-4"
            elif "💥 TRADE WITH DESMOND!" in message_text:
                source = "Cameroon"
            result['source'] = source

            if timezone_convert:
                entry_utc = timezone_convert(entry_time_str, source)
                if not entry_utc:
                    log_info(f"[⚠️] Signal entry time {entry_time_str} already passed, skipping.")
                    return None
                result['entry_time'] = entry_utc
            else:
                result['entry_time'] = entry_time_str

        # Timeframe
        timeframe_match = re.search(r'Expiration:?\s*(M1|M5|1 Minute|5 Minute|5M|1M|5-minute)', message_text, re.IGNORECASE)
        if timeframe_match:
            tf = timeframe_match.group(1).lower()
            result['timeframe'] = 'M1' if '1' in tf else 'M5'
        if not result['timeframe']:
            result['timeframe'] = 'M1' if is_anna_signal else 'M5'

        # Martingale times
        martingale_matches = re.findall(
            r'(?:Level \d+|level(?: at)?|PROTECTION|level At|level|ª PROTECTION)\D*[:\-\—>]*\s*(\d{2}:\d{2})',
            message_text, re.IGNORECASE
        )
        martingale_utc_times = []
        for t in martingale_matches:
            if timezone_convert:
                t_utc = timezone_convert(t, result['source'])
                if t_utc:
                    martingale_utc_times.append(t_utc)
        result['martingale_times'] = martingale_utc_times

        # Default Anna martingale if none found
        if is_anna_signal and not result['martingale_times'] and result['entry_time']:
            entry_dt = result['entry_time']
            interval = timedelta(minutes=1)
            first_mg = entry_dt + interval
            second_mg = first_mg + interval
            result['martingale_times'] = [first_mg, second_mg]
            log_info(f"[🔁] Default Anna martingale times applied: {[t.strftime('%H:%M') for t in result['martingale_times']]}")

        if not result['currency_pair'] or not result['entry_time'] or not result['direction']:
            return None

        return result

    except Exception as e:
        log_error(f"[❌] Error parsing signal: {e}")
        return None

# =========================
# Telegram Listener
# =========================
def start_telegram_listener(signal_callback, command_callback):
    log_info("[🔌] Starting Telegram listener...")

    @client.on(events.NewMessage(chats=TARGET_CHAT_ID))
    async def handler(event):
        try:
            text = event.message.message

            if text.startswith("/start") or text.startswith("/stop"):
                log_info(f"[💻] Command detected: {text}")
                await command_callback(text)
                return

            signal = parse_signal(text)
            if signal:
                received_time = datetime.utcnow().strftime("%H:%M:%S")
                log_info(f"[⚡] Parsed signal at {received_time}: {signal}")
                await signal_callback(signal)
            else:
                log_info("[ℹ️] Message ignored (not a valid signal).")

        except Exception as e:
            log_error(f"[❌] Error handling message: {e}")

    try:
        log_info("[⚙️] Connecting to Telegram...")
        client.start(bot_token=bot_token)
        log_info("[✅] Connected to Telegram. Listening for messages...")
        client.run_until_disconnected()
    except Exception as e:
        log_error(f"[❌] Telegram listener failed: {e}")

# =========================
# Entry Point
# =========================
if __name__ == "__main__":
    log_info("[🚀] Telegram listener script started.")

    try:
        # ✅ Import callbacks from telegram_callbacks.py
        from telegram_callbacks import signal_callback, command_callback
    except ImportError as e:
        log_error(f"[❌] Failed to import telegram_callbacks: {e}")
        raise

    # ✅ Start the listener (this keeps the process alive)
    try:
        start_telegram_listener(signal_callback, command_callback)
    except Exception as e:
        log_error(f"[❌] Telegram listener crashed: {e}")
        raise
                             
