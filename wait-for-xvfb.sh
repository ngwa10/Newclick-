#!/bin/bash

# -----------------------
# wait-for-xvfb.sh
# -----------------------

set -e
export DISPLAY=:1
export XAUTHORITY=/tmp/.Xauthority

echo "[🕒] Waiting for Xvfb to start on DISPLAY=$DISPLAY..."

MAX_RETRIES=60
RETRY_INTERVAL=1
COUNT=0

while ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; do
    sleep "$RETRY_INTERVAL"
    COUNT=$((COUNT + 1))
    echo "[⏳] Attempt $COUNT: Xvfb not ready yet..."

    if [ "$COUNT" -ge "$MAX_RETRIES" ]; then
        echo "[❌] Xvfb did not start within expected time. Exiting."
        exit 1
    fi
done

echo "[✅] Xvfb is ready on DISPLAY=$DISPLAY!"

# 🧠 IMPORTANT: Only run bot.py here (not core.py)
echo "[🚀] Starting bot.py for WebDriver setup..."
exec python3 /app/bot.py
