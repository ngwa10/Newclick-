#!/bin/bash
# Ensure display environment variables are set for PyAutoGUI and Chrome
export DISPLAY=:1
export XAUTHORITY=/tmp/.Xauthority

echo "[🚀] Starting bot.py..."

# Optional: wait a few seconds for Xvfb and Chrome to fully start
sleep 5

# Run the Python script
python3 /app/bot.py
