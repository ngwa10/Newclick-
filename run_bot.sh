#!/bin/bash
# -----------------------
# run_bot.sh
# -----------------------

# Exit immediately if a command exits with a non-zero status
set -e

# -----------------------
# Environment setup
# -----------------------
export XAUTHORITY=/tmp/.Xauthority
export DISPLAY=:1

# Ensure .Xauthority exists
if [ ! -f "$XAUTHORITY" ]; then
    touch "$XAUTHORITY"
    echo "[⚠️] Created empty $XAUTHORITY. Ensure Xvfb is running."
fi

# Optional: verify Xvfb / X server is running
if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    echo "[❌] X server not detected on DISPLAY=$DISPLAY"
    exit 1
fi

echo "[🚀] Starting core.py bot..."

# Run the main bot script
# Use python3 explicitly to avoid conflicts with python2
python3 core.py
