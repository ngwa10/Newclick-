#!/bin/bash
# wait_for_vnc.sh
# Wait until the VNC server is running before starting noVNC proxy.

echo "[wait_for_vnc] Waiting for VNC server on port 5901..."

# Wait for VNC port with timeout
timeout=60
while ! nc -z localhost 5901 && [ $timeout -gt 0 ]; do
  sleep 1
  timeout=$((timeout - 1))
done

if [ $timeout -eq 0 ]; then
  echo "[❌] Timeout waiting for VNC server"
  exit 1
fi

echo "[wait_for_vnc] ✅ VNC server detected. Launching noVNC..."

# Start noVNC proxy and listen on all interfaces
exec /opt/noVNC/utils/novnc_proxy --vnc localhost:5901 --listen 0.0.0.0:6080 --web /opt/noVNC
