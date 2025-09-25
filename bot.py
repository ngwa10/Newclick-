import time
import pyautogui
import os
import subprocess
import re

# -----------------------
# Settings
# -----------------------
TRADE_INTERVAL = 10       # seconds between trading cycles
LOGIN_WAIT = 300          # 5 minutes to log in manually

# -----------------------
# Helper: find Chrome window center
# -----------------------
def get_chrome_window_center():
    """
    Uses wmctrl to find Chrome window in Xvfb and returns center coordinates.
    """
    try:
        output = subprocess.check_output(['wmctrl', '-lG']).decode()
        for line in output.splitlines():
            if 'Google Chrome' in line:
                parts = line.split()
                x, y = int(parts[2]), int(parts[3])
                w, h = int(parts[4]), int(parts[5])
                center_x = x + w // 2
                center_y = y + h // 2
                return center_x, center_y
    except Exception as e:
        print(f"[❌] Error finding Chrome window: {e}")
    # Fallback to screen center
    return 960, 540

# -----------------------
# Startup
# -----------------------
print("[ℹ️] Bot started. Waiting for manual login...")
time.sleep(LOGIN_WAIT)

# Ensure Chrome window is focused
click_x, click_y = get_chrome_window_center()
pyautogui.click(x=click_x, y=click_y)
time.sleep(1)

print("[🚀] Starting automated hotkey trading loop...")

# -----------------------
# Main trading loop
# -----------------------
while True:
    try:
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[💓 Heartbeat] Bot is alive at {current_time}")

        # 1️⃣ Increase trade amount: Shift + D
        pyautogui.keyDown('shift')
        pyautogui.press('d')
        pyautogui.keyUp('shift')
        print(f"[✅ {current_time}] Increased trade amount")

        # 2️⃣ Buy trade: Shift + W
        pyautogui.keyDown('shift')
        pyautogui.press('w')
        pyautogui.keyUp('shift')
        print(f"[✅ {current_time}] Buy trade executed")

        # 3️⃣ Switch to next favorite asset: Shift + TAB
        pyautogui.keyDown('shift')
        pyautogui.press('tab')
        pyautogui.keyUp('shift')
        print(f"[✅ {current_time}] Switched to next asset")

        # Wait before next cycle
        time.sleep(TRADE_INTERVAL)

    except Exception as e:
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[❌ {current_time}] Error in trading loop: {e}")
        time.sleep(5)
