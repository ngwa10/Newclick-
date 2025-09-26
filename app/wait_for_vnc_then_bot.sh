#!/bin/bash
# wait_for_vnc_then_bot.sh
# Wait until the VNC server is up before launching the bot.

echo "[wait_for_vnc_then_bot] Waiting for VNC server before launching the bot..."

# Wait for VNC port
while ! nc -z localhost 5901; do
  sleep 1
done

echo "[wait_for_vnc_then_bot] ✅ VNC server is up. Starting bot..."

# Start your bot
exec /app/run_bot.sh
