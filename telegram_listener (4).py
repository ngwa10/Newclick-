"""
Telegram listener with integrated parsing + timezone handling.
Forwards signals directly to core.signal_callback(...) and commands
to shared.trade_manager.handle_command(...).

Filename: Telegram listener..py
"""

from telethon import TelegramClient, events
import re
from datetime import datetime, timedelta
import logging
import traceback

# Hard-coded credentials (keep as before)
api_id = 29630724
api_hash = "8e12421a95fd722246e0c0b194fd3e0c"
bot_token = "8477806088:AAGEXpIAwN5tNQM0hsCGqP-otpLJjPJLmWA"
TARGET_CHAT_ID = -1003033183667  # Numeric channel ID

# Logging setup (matches your style)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("telegram_listener")

def log_info(msg):
    logger.info(msg)
    for h in logger.handlers:
        try:
            h.flush()
        except Exception:
            pass

def log_error(msg):
    logger.error(msg)
    for h in logger.handlers:
        try:
            h.flush()
        except Exception:
            pass

# Import core and shared so we can forward signals and commands
try:
    import core
    import shared
except Exception as e:
    log_error(f"[❌] Failed to import core/shared: {e}")
    raise

# Try to import timezone_convert from core_utils if available
try:
    from core_utils import timezone_convert
except Exception:
    timezone_convert = None
    log_error("[⚠️] core_utils.timezone_convert not found, signals will use local/naive conversion fallback")

# ---------------------------
# Signal parsing (full logic from your previous code)
# ---------------------------
def parse_signal(message_text: str):
    """
    Parses the message_text for various signal formats (Anna, OTC, Precision).
    Returns a dict with keys:
      currency_pair, direction, entry_time (datetime tz-aware if timezone_convert used),
      timeframe, martingale_times (list of datetimes), source
    or returns None if the message doesn't contain a valid signal.
    """
    try:
        result = {
            "currency_pair": None,
            "direction": None,
            "entry_time": None,
            "timeframe": None,
            "martingale_times": [],
            "source": "OTC-3"
        }

        # quick filter
        if not re.search(r'(BUY|SELL|CALL|PUT|🔼|🟥|🟩|🔽|✅ ANNA SIGNALS ✅|_OTC)', message_text, re.IGNORECASE):
            return None

        is_anna_signal = "anna signals" in message_text.lower()
        clean_text = re.sub(r'[^\x00-\x7F]+', ' ', message_text)  # remove non-ascii emojis for some regexes

        # Currency Pair
        pair_match = re.search(r'([A-Z]{3}/[A-Z]{3})(?:[\s_\-]?OTC)?', clean_text, re.IGNORECASE)
        if pair_match:
            result['currency_pair'] = pair_match.group(1).strip().upper()

        # Direction
        direction_match = re.search(r'(BUY|SELL|CALL|PUT|🔼|🟥|🟩|🔽|⏺ BUY|⏺ SELL)', message_text, re.IGNORECASE)
        if direction_match:
            direction = direction_match.group(1).upper()
            if direction in ['CALL', 'BUY', '🟩', '🔼', '⏺ BUY']:
                result['direction'] = 'BUY'
            elif direction in ['PUT', 'SELL', '🔽', '🟥', '⏺ SELL']:
                result['direction'] = 'SELL'

        # Source detection (keeps your mapping)
        source = "OTC-3"
        if "💥 GET THIS SIGNAL HERE!" in message_text:
            source = "UTC-4"
        elif "💥 TRADE WITH DESMOND!" in message_text:
            source = "Cameroon"
        result['source'] = source

        # Entry Time (various labels)
        entry_time_match = re.search(
            r'(?:Entry Time:|Entry at|TIME \(UTC.*\):|⏺ Entry at|Entry:)\s*(\d{2}:\d{2})',
            message_text, re.IGNORECASE
        )
        if entry_time_match:
            entry_time_str = entry_time_match.group(1)
            # Prefer using timezone_convert if available
            if timezone_convert:
                converted = timezone_convert(entry_time_str, source)
                if not converted:
                    log_info(f"[⚠️] Signal entry time {entry_time_str} appears to already have passed or is invalid; skipping.")
                    return None
                result['entry_time'] = converted
            else:
                # naive fallback: create a datetime in UTC by parsing HH:MM as UTC today
                try:
                    hh, mm = map(int, entry_time_str.split(":"))
                    now = datetime.utcnow()
                    entry_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                    # attach UTC tzinfo so downstream expects tz-aware whenever timezone_convert used
                    try:
                        import pytz
                        entry_dt = pytz.UTC.localize(entry_dt)
                    except Exception:
                        pass
                    result['entry_time'] = entry_dt
                except Exception:
                    log_error(f"[❌] Failed naïve parse of entry_time '{entry_time_str}'")
                    return None

        # Timeframe
        timeframe_match = re.search(r'Expiration:?\s*(M1|M5|1 Minute|5 Minute|5M|1M|5-minute)', message_text, re.IGNORECASE)
        if timeframe_match:
            tf = timeframe_match.group(1).lower()
            result['timeframe'] = 'M1' if '1' in tf else 'M5'
        if not result['timeframe']:
            result['timeframe'] = 'M1' if is_anna_signal else 'M5'

        # Martingale times extraction (many formats)
        martingale_matches = re.findall(
            r'(?:Level \d+|level(?: at)?|PROTECTION|level At|level|ª PROTECTION)\D*[:\-\—>]*\s*(\d{2}:\d{2})',
            message_text, re.IGNORECASE
        )
        mg_times = []
        for t in martingale_matches:
            if timezone_convert and result.get('source'):
                converted = timezone_convert(t, result['source'])
                if converted:
                    mg_times.append(converted)
            else:
                # naive fallback (UTC)
                try:
                    hh, mm = map(int, t.split(":"))
                    now = datetime.utcnow()
                    mg_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                    try:
                        import pytz
                        mg_dt = pytz.UTC.localize(mg_dt)
                    except Exception:
                        pass
                    mg_times.append(mg_dt)
                except Exception:
                    log_error(f"[⚠️] Failed naive parse of martingale time '{t}'")
        result['martingale_times'] = mg_times

        # If Anna signals and no martingale times found, create defaults (+1m, +2m)
        if is_anna_signal and not result['martingale_times'] and result['entry_time']:
            interval = timedelta(minutes=1)
            first_mg = result['entry_time'] + interval
            second_mg = first_mg + interval
            result['martingale_times'] = [first_mg, second_mg]
            log_info(f"[🔁] Default Anna martingale times applied: {[t.strftime('%H:%M') for t in result['martingale_times']]}")

        # Final sanity check
        if not result['currency_pair'] or not result['direction'] or not result['entry_time']:
            return None

        return result

    except Exception as e:
        tb = traceback.format_exc()
        log_error(f"[❌] Error parsing signal: {e}\n{tb}")
        return None

# ---------------------------
# Telegram listener and forwarding
# ---------------------------
def start_telegram_listener():
    log_info("[🔌] Starting Telegram listener (integrated) ...")
    client = TelegramClient('bot_session', api_id, api_hash)

    @client.on(events.NewMessage(chats=TARGET_CHAT_ID))
    async def handler(event):
        try:
            text = event.message.message or ""
            # Commands
            if text.startswith("/start") or text.startswith("/stop"):
                log_info(f"[💻] Command detected: {text}")
                # Forward command to TradeManager if present
                try:
                    # prefer core-level API if available, otherwise shared.trade_manager
                    if hasattr(core, "handle_command"):
                        # core.py doesn't define handle_command wrapper; use shared.trade_manager
                        pass
                except Exception:
                    pass

                # Use shared.trade_manager.handle_command when available
                try:
                    if shared.trade_manager is not None:
                        shared.trade_manager.handle_command(text)
                        log_info(f"[✅] Command forwarded to TradeManager: {text}")
                    else:
                        log_error("[⚠️] TradeManager not ready; command ignored.")
                except Exception as e:
                    log_error(f"[❌] Failed to forward command: {e}")
                return

            # Signals
            parsed = parse_signal(text)
            if parsed:
                recv_time = datetime.utcnow().strftime("%H:%M:%S")
                log_info(f"[⚡] Parsed signal at {recv_time}: {parsed}")

                # Forward to core.signal_callback if exists (core provides signal_callback wrapper)
                try:
                    if hasattr(core, "signal_callback"):
                        core.signal_callback(parsed)
                        log_info("[🤖] Sent to core.signal_callback")
                    else:
                        # last-resort: shared.trade_manager
                        if shared.trade_manager is not None:
                            shared.trade_manager.handle_signal(parsed)
                            log_info("[🤖] Sent to shared.trade_manager.handle_signal")
                        else:
                            log_error("[⚠️] TradeManager not ready; signal queued or ignored (no queue active).")
                except Exception as e:
                    log_error(f"[❌] Error forwarding signal to core: {e}")
                    log_error(traceback.format_exc())
            else:
                log_info("[ℹ️] Message ignored (not a valid signal).")

        except Exception as e:
            log_error(f"[❌] Error handling message: {e}\n{traceback.format_exc()}")

    try:
        log_info("[⚙️] Connecting to Telegram...")
        client.start(bot_token=bot_token)
        log_info("[✅] Connected to Telegram. Listening for messages...")
        client.run_until_disconnected()
    except Exception as e:
        log_error(f"[❌] Telegram listener failed: {e}\n{traceback.format_exc()}")

# ---------------------------
# Entry point
# ---------------------------
if __name__ == "__main__":
    log_info("[🚀] Telegram listener (integrated) script started.")
    start_telegram_listener()
            
