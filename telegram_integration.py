"""
Telegram integration: Listener and signal parser.
Includes runtime logging for connection, messages, and errors.
"""

from telethon import TelegramClient, events
import os
import re
from datetime import datetime, timedelta

# Load credentials from environment
api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
channel_env = os.getenv("TELEGRAM_CHANNEL")  # Can be numeric ID (-100...) or username (@channelname)

client = TelegramClient('bot_session', api_id, api_hash)

# Resolve channel once at startup
channel_entity = None

async def resolve_channel():
    global channel_entity
    try:
        if channel_env.startswith("-100") or channel_env.lstrip("-").isdigit():
            channel_entity = await client.get_entity(int(channel_env))
        else:
            channel_entity = await client.get_entity(channel_env)
        print(f"[✅] Resolved channel: {channel_entity.title if hasattr(channel_entity, 'title') else channel_entity.id}")
    except Exception as e:
        print(f"[❌] Failed to resolve Telegram channel '{channel_env}': {e}")
        raise

def start_telegram_listener(signal_callback, command_callback):
    print("[🔌] Starting Telegram listener...")

    @client.on(events.NewMessage())
    async def handler(event):
        # Only process messages from the target channel
        target_id = getattr(channel_entity, 'id', None)
        if event.chat_id != target_id:
            return

        text = event.message.message
        print(f"[📩] New message received: {text}")

        if text.startswith("/start") or text.startswith("/stop"):
            print(f"[💻] Command detected: {text}")
            await command_callback(text)
        else:
            signal = parse_signal(text)
            if signal['currency_pair'] and signal['entry_time']:
                print(f"[⚡] Parsed signal: {signal}")
                await signal_callback(signal)

    try:
        print("[⚙️] Connecting to Telegram...")
        client.start(bot_token=bot_token)
        print("[✅] Connected to Telegram. Resolving channel...")
        client.loop.run_until_complete(resolve_channel())
        print("[✅] Listening for messages...")
        client.run_until_disconnected()
    except Exception as e:
        print(f"[❌] Telegram listener failed: {e}")


def parse_signal(message_text):
    """
    Parses trading signals from a Telegram message text.
    Returns a dictionary with:
    currency_pair, direction, entry_time, timeframe, martingale_times
    """
    result = {
        "currency_pair": None,
        "direction": None,
        "entry_time": None,
        "timeframe": None,
        "martingale_times": []
    }

    # Currency pair
    pair_match = re.search(r'(?:Pair:|CURRENCY PAIR:|🇺🇸|📊)\s*([\w\/\-]+)', message_text)
    if pair_match:
        result['currency_pair'] = pair_match.group(1).strip()

    # Direction
    direction_match = re.search(r'(BUY|SELL|CALL|PUT|🔼|🟥|🟩)', message_text, re.IGNORECASE)
    if direction_match:
        direction = direction_match.group(1).upper()
        if direction in ['CALL', 'BUY', '🟩', '🔼']:
            result['direction'] = 'BUY'
        else:
            result['direction'] = 'SELL'

    # Entry time
    entry_time_match = re.search(r'(?:Entry Time:|Entry at|TIME \(UTC-03:00\):)\s*(\d{2}:\d{2}(?::\d{2})?)', message_text)
    if entry_time_match:
        result['entry_time'] = entry_time_match.group(1)

    # Timeframe
    timeframe_match = re.search(r'Expiration:?\s*(M1|M5|1 Minute|5 Minute)', message_text)
    if timeframe_match:
        tf = timeframe_match.group(1)
        result['timeframe'] = 'M1' if tf in ['M1', '1 Minute'] else 'M5'

    # Martingale times
    martingale_matches = re.findall(r'(?:Level \d+|level(?: at)?|PROTECTION).*?\s*(\d{2}:\d{2})', message_text)
    result['martingale_times'] = martingale_matches

    # Default Anna signals martingale logic (2 levels)
    if "anna signals" in message_text.lower() and not result['martingale_times']:
        fmt = "%H:%M:%S" if result['entry_time'] and len(result['entry_time']) == 8 else "%H:%M"
        entry_dt = datetime.strptime(result['entry_time'], fmt)
        interval = 1 if result['timeframe'] == "M1" else 5
        result['martingale_times'] = [
            (entry_dt + timedelta(minutes=interval * i)).strftime(fmt)
            for i in range(1, 3)
        ]
        print(f"[🔁] Default Anna martingale times applied: {result['martingale_times']}")

    return result
        
