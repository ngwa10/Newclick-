# EDIT

"""
Telegram integration: Listener and signal parser.
"""

from telethon import TelegramClient, events
import os
import re
from datetime import datetime, timedelta

api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")
channel = os.getenv("TELEGRAM_CHANNEL")
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
client = TelegramClient('session_name', api_id, api_hash)

def start_telegram_listener(signal_callback, command_callback):
    @client.on(events.NewMessage(chats=channel))
    async def handler(event):
        text = event.message.message
        if text.startswith("/start") or text.startswith("/stop"):
            await command_callback(text)
        else:
            signal = parse_signal(text)
            if signal['currency_pair'] and signal['entry_time']:
                await signal_callback(signal)
    client.start(bot_token=bot_token)
    client.run_until_disconnected()

def parse_signal(message_text):
    result = {
        "currency_pair": None,
        "direction": None,
        "entry_time": None,
        "timeframe": None,
        "martingale_times": []
    }
    pair_match = re.search(r'(?:Pair:|CURRENCY PAIR:|🇺🇸|📊)\s*([\w\/\-]+)', message_text)
    if pair_match:
        result['currency_pair'] = pair_match.group(1).strip()
    direction_match = re.search(r'(BUY|SELL|CALL|PUT|🔼|🟥|🟩)', message_text, re.IGNORECASE)
    if direction_match:
        direction = direction_match.group(1).upper()
        if direction in ['CALL', 'BUY', '🟩', '🔼']:
            result['direction'] = 'BUY'
        else:
            result['direction'] = 'SELL'
    entry_time_match = re.search(r'(?:Entry Time:|Entry at|TIME \(UTC-03:00\):)\s*(\d{2}:\d{2}(?::\d{2})?)', message_text)
    if entry_time_match:
        result['entry_time'] = entry_time_match.group(1)
    timeframe_match = re.search(r'Expiration:?\s*(M1|M5|1 Minute|5 Minute)', message_text)
    if timeframe_match:
        tf = timeframe_match.group(1)
        result['timeframe'] = 'M1' if tf in ['M1', '1 Minute'] else 'M5'
    martingale_matches = re.findall(r'(?:Level \d+|level(?: at)?|PROTECTION).*?\s*(\d{2}:\d{2})', message_text)
    result['martingale_times'] = martingale_matches

    # --- Anna signals default martingale logic (2 Levels) ---
    if "anna signals" in message_text.lower() and not result['martingale_times']:
        # Attach default martingale levels (2 levels)
        fmt = "%H:%M:%S" if result['entry_time'] and len(result['entry_time']) == 8 else "%H:%M"
        entry_dt = datetime.strptime(result['entry_time'], fmt)
        interval = 1 if result['timeframe'] == "M1" else 5
        result['martingale_times'] = [
            (entry_dt + timedelta(minutes=interval * i)).strftime("%H:%M:%S") if fmt == "%H:%M:%S"
            else (entry_dt + timedelta(minutes=interval * i)).strftime("%H:%M")
            for i in range(1, 3)  # 2 martingale levels (after entry)
        ]
    return result
