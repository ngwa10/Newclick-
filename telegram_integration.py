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
channel_env = os.getenv("TELEGRAM_CHANNEL")  # Could be integer ID or username

client = TelegramClient('session_name', api_id, api_hash)

async def get_channel_entity():
    """
    Resolves the Telegram channel to an entity.
    Works for integer ID or username string.
    """
    try:
        if channel_env.isdigit():
            # If numeric ID, convert to int
            entity = await client.get_input_entity(int(channel_env))
        else:
            # If username string, pass as-is
            entity = await client.get_input_entity(channel_env)
        return entity
    except Exception as e:
        print(f"[❌] Failed to resolve Telegram channel '{channel_env}': {e}")
        raise

def start_telegram_listener(signal_callback, command_callback):
    print("[🔌] Starting Telegram listener...")

    @client.on(events.NewMessage())
    async def handler(event):
        # Ensure the message comes from our target channel
        try:
            entity = await get_channel_entity()
        except Exception:
            return  # Skip if channel resolution failed

        if event.chat_id != entity.channel_id:
            return  # Ignore messages from other chats

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
        print("[✅] Connected to Telegram. Listening for messages...")
        client.run_until_disconnected()
    except Exception as e:
        print(f"[❌] Telegram listener failed: {e}")

# parse_signal() remains unchanged
