# telegram_integration.py
"""
Telegram integration: Listener and signal parser.
Includes automatic .env loading and runtime logs.
"""

import os
import re
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from dotenv import load_dotenv

# -----------------------
# Load environment variables
# -----------------------
env_path = '/app/.env'
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"[🟢] Loaded environment variables from {env_path}")
else:
    print(f"[⚠️] .env file not found at {env_path}, relying on system environment variables")

# Read Telegram credentials
api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
channel = os.getenv("TELEGRAM_CHANNEL")

print(f"[🔑] Telegram API ID: {'SET' if api_id else 'MISSING'}")
print(f"[🔑] Telegram API HASH: {'SET' if api_hash else 'MISSING'}")
print(f"[🔑] Telegram BOT TOKEN: {'SET' if bot_token else 'MISSING'}")
print(f"[🔑] Telegram CHANNEL: {channel if channel else 'MISSING'}")

if not api_id or not api_hash:
    raise ValueError("Telegram API ID or HASH missing. Check your .env file or environment variables.")

# Initialize client
client = TelegramClient('session_name', api_id, api_hash)

# -----------------------
# Listener
# -----------------------
def start_telegram_listener(signal_callback, command_callback):
    @client.on(events.NewMessage(chats=channel))
    async def handler(event):
        text = event.message.message
        print(f"[📩] New message received: {text}")
        try:
            if text.startswith("/start") or text.startswith("/stop"):
                print(f"[📢] Command detected: {text}")
                await command_callback(text)
            else:
                signal = parse_signal(text)
                if signal['currency_pair'] and signal['entry_time']:
                    print(f"[⚡] Signal parsed: {signal}")
                    await signal_callback(signal)
        except Exception as e:
            print(f"[❌] Error handling message: {e}")

    print("[🟢] Starting Telegram client...")
    client.start(bot_token=bot_token)
    client.run_until_disconnected()

# -----------------------
# Signal parser
# -----------------------
def parse_signal(message_text):
    result = {
        "currency_pair": None,
        "direction": None,
        "entry_time": None,
        "timeframe": None,
        "martingale_times": []
    }

    # Parse currency pair
    pair_match = re.search(r'(?:Pair:|CURRENCY PAIR:|🇺🇸|📊)\s*([\w\/\-]+)', message_text)
    if pair_match:
        result['currency_pair'] = pair_match.group(1).strip()

    # Parse direction
    direction_match = re.search(r'(BUY|SELL|CALL|PUT|🔼|🟥|🟩)', message_text, re.IGNORECASE)
    if direction_match:
        direction = direction_match.group(1).upper()
        if direction in ['CALL', 'BUY', '🟩', '🔼']:
            result['direction'] = 'BUY'
        else:
            result['direction'] = 'SELL'

    # Parse entry time
    entry_time_match = re.search(r'(?:Entry Time:|Entry at|TIME \(UTC-03:00\):)\s*(\d{2}:\d{2}(?::\d{2})?)', message_text)
    if entry_time_match:
        result['entry_time'] = entry_time_match.group(1)

    # Parse timeframe
    timeframe_match = re.search(r'Expiration:?\s*(M1|M5|1 Minute|5 Minute)', message_text)
    if timeframe_match:
        tf = timeframe_match.group(1)
        result['timeframe'] = 'M1' if tf in ['M1', '1 Minute'] else 'M5'

    # Parse martingale times
    martingale_matches = re.findall(r'(?:Level \d+|level(?: at)?|PROTECTION).*?\s*(\d{2}:\d{2})', message_text)
    result['martingale_times'] = martingale_matches

    # Default martingale for Anna signals
    if "anna signals" in message_text.lower() and not result['martingale_times']:
        fmt = "%H:%M:%S" if result['entry_time'] and len(result['entry_time']) == 8 else "%H:%M"
        entry_dt = datetime.strptime(result['entry_time'], fmt)
        interval = 1 if result['timeframe'] == "M1" else 5
        result['martingale_times'] = [
            (entry_dt + timedelta(minutes=interval * i)).strftime(fmt)
            for i in range(1, 3)
        ]

    return result
