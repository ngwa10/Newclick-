import time
import pyautogui
import os

# -----------------------
# Settings
# -----------------------
# Coordinates to click on Chrome window inside Xvfb (center of 1920x1080)
CLICK_X = 960
CLICK_Y = 540

# Interval between each trading cycle (seconds)
TRADE_INTERVAL = 10

# Initial wait to log in manually via noVNC (seconds)
LOGIN_WAIT = 300  # 5 minutes

# -----------------------
# Startup
# -----------------------
print("[ℹ️] Bot started. Waiting for manual login...")
time.sleep(LOGIN_WAIT)

# Focus Chrome window by clicking center
pyautogui.click(x=CLICK_X, y=CLICK_Y)
time.sleep(1)

print("[🚀] Starting automated hotkey trading loop...")

# -----------------------
# Main trading loop
# -----------------------
while True:
    try:
        print(f"[ℹ️] Bot status: Running. Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 1️⃣ Increase trade amount: Shift + D
        pyautogui.keyDown('shift')
        pyautogui.press('d')
        pyautogui.keyUp('shift')
        print("[✅] Increased trade amount")
        time.sleep(1)

        # 2️⃣ Buy trade: Shift + W
        pyautogui.keyDown('shift')
        pyautogui.press('w')
        pyautogui.keyUp('shift')
        print("[✅] Buy trade executed")
        time.sleep(1)

        # 3️⃣ Switch to next favorite asset: Shift + TAB
        pyautogui.keyDown('shift')
        pyautogui.press('tab')
        pyautogui.keyUp('shift')
        print("[✅] Switched to next asset")

        # Wait before next cycle
        time.sleep(TRADE_INTERVAL)

    except Exception as e:
        print(f"[❌] Error in trading loop: {e}")
        time.sleep(5)
        
