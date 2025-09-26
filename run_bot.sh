#!/bin/bash
# -----------------------
# run_bot.sh
# -----------------------

# Fail immediately if a command fails
set -e

# Ensure Xauthority and DISPLAY are set
export XAUTHORITY=/tmp/.Xauthority
export DISPLAY=:1

# Optional: verify Xvfb is running
if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    echo "[❌] X server not detected on DISPLAY=$DISPLAY"
    exit 1
fi

echo "[🚀] Starting core.py bot..."

# Run the main bot script from root directory
python3 core.py
