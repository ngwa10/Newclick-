#!/bin/bash
# Ensure display environment variables are set
export DISPLAY=:1
export XAUTHORITY=/tmp/.Xauthority

# Create .Xauthority if it does not exist
if [ ! -f /tmp/.Xauthority ]; then
    touch /tmp/.Xauthority
    chmod 600 /tmp/.Xauthority
    echo "[WARN] Created empty .Xauthority file"
fi

echo "[🚀] Starting bot.py..."
sleep 5  # Wait for Xvfb to be fully ready

python3 /app/bot.py
