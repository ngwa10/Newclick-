#!/bin/bash
# wait_for_vnc.sh
# Wait until the VNC server is running before starting noVNC proxy.

echo "[wait_for_vnc] Waiting for VNC server on port 5901..."

# Wait for VNC port
while ! nc -z localhost 5901; do
  sleep 1
done

echo "[wait_for_vnc] ✅ VNC server detected. Launching noVNC..."

# Start noVNC proxy
exec /opt/noVNC/utils/novnc_proxy --vnc localhost:5901 --listen 6080 --web /opt/noVNC
