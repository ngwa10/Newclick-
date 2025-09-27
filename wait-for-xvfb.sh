#!/bin/bash

# -----------------------
# wait-for-xvfb.sh
# -----------------------

# Exit immediately if a command exits with a non-zero status
set -e

# Set display environment variable
export DISPLAY=:1

echo "[🕒] Waiting for Xvfb to start on DISPLAY=$DISPLAY..."

# Loop until Xvfb is ready
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

# Launch your bot
echo "[🚀] Starting bot..."
exec python3 /app/core.py T
