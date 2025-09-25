import os
import time
import pyautogui
import subprocess

# -----------------------
# Set DISPLAY for Xvfb
# -----------------------
os.environ['DISPLAY'] = ':1'

# -----------------------
# User Credentials
# -----------------------
EMAIL = "mylivemyfuture@123gmail.com"
PASSWORD = "AaCcWw3468,"

# -----------------------
# Settings
# -----------------------
TRADE_INTERVAL = 10       # seconds between trading cycles
LOGIN_WAIT = 5            # wait for Chrome to render fully
POST_LOGIN_WAIT = 5       # wait after manual login

# -----------------------
# Helper: find Chrome window
# -----------------------
def get_chrome_window_position():
    """
    Uses wmctrl to find Chrome window in Xvfb and returns top-left coordinates and size.
    """
    try:
        output = subprocess.check_output(['wmctrl', '-lG']).decode()
        for line in output.splitlines():
            if 'Google Chrome' in line:
                parts = line.split()
                x, y = int(parts[2]), int(parts[3])
                w, h = int(parts[4]), int(parts[5])
                return x, y, w, h
    except Exception as e:
        print(f"[❌] Error finding Chrome window: {e}")
    return 0, 0, 1920, 1080

# -----------------------
# Wait for Chrome to appear
# -----------------------
def wait_for_chrome(timeout=60):
    for _ in range(timeout):
        x, y, w, h = get_chrome_window_position()
        if w > 0 and h > 0:
            return True
        time.sleep(1)
    return False

# -----------------------
# Fill login credentials
# -----------------------
def fill_login():
    x, y, w, h = get_chrome_window_position()
    print(f"[ℹ️] Chrome window position: {x},{y},{w},{h}")

    email_x = x + int(w * 0.5)
    email_y = y + int(h * 0.35)
    password_x = x + int(w * 0.5)
    password_y = y + int(h * 0.45)

    pyautogui.click(email_x, email_y)
    pyautogui.write(EMAIL, interval=0.05)
    time.sleep(0.5)

    pyautogui.click(password_x, password_y)
    pyautogui.write(PASSWORD, interval=0.05)
    time.sleep(0.5)

    print("[✅] Credentials filled. Please click Login manually.")

# -----------------------
# Focus Chrome window
# -----------------------
def focus_chrome():
    x, y, w, h = get_chrome_window_position()
    center_x = x + w // 2
    center_y = y + h // 2
    pyautogui.click(center_x, center_y)
    time.sleep(1)

# -----------------------
# Main
# -----------------------
print("[ℹ️] Waiting for Chrome window to appear...")
if not wait_for_chrome():
    print("[❌] Chrome window not found. Exiting.")
    exit(1)

fill_login()

print("[ℹ️] Waiting for manual login...")
time.sleep(POST_LOGIN_WAIT)

focus_chrome()

print("[🚀] Starting automated hotkey trading loop...")

while True:
    try:
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[💓 Heartbeat] Bot is alive at {current_time}")

        # Increase trade amount: Shift + D
        pyautogui.keyDown('shift')
        pyautogui.press('d')
        pyautogui.keyUp('shift')
        print(f"[✅ {current_time}] Increased trade amount")

        # Buy trade: Shift + W
        pyautogui.keyDown('shift')
        pyautogui.press('w')
        pyautogui.keyUp('shift')
        print(f"[✅ {current_time}] Buy trade executed")

        # Switch to next asset: Shift + TAB
        pyautogui.keyDown('shift')
        pyautogui.press('tab')
        pyautogui.keyUp('shift')
        print(f"[✅ {current_time}] Switched to next asset")

        time.sleep(TRADE_INTERVAL)

    except Exception as e:
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[❌ {current_time}] Error in trading loop: {e}")
        time.sleep(5)
                                          
