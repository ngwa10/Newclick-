import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Headless=False so we can see the browser via VNC
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--remote-debugging-port=9222")  # required

# Connect to local Chrome (Selenium server runs at 4444)
driver = webdriver.Remote(
    command_executor="http://localhost:4444/wd/hub",
    options=chrome_options
)
wait = WebDriverWait(driver, 60)  # wait for manual login

try:
    # Open login page
    print("[INFO] Opened login page. Please log in manually using VNC...")
    driver.get("https://pocketoption.com/en/login/")

    # Wait for dashboard
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'balance')]")))
        print("[SUCCESS] Dashboard detected! Continuing automation...")
    except TimeoutException:
        print("[ERROR] Dashboard not detected in time. Screenshot saved.")
        driver.save_screenshot("manual_login_error.png")
        driver.quit()
        exit(1)

    # Navigate to demo quick trading
    driver.get("https://pocketoption.com/en/cabinet/demo-quick-high-low/")

    # Wait for canvas
    canvas = None
    for i in range(5):
        try:
            canvas = wait.until(EC.presence_of_element_located((By.TAG_NAME, "canvas")))
            break
        except TimeoutException:
            print(f"[WARN] Canvas not ready yet (attempt {i+1}/5)...")
            time.sleep(3)

    if not canvas:
        print("[ERROR] Canvas not found after retries. Exiting.")
        driver.quit()
        exit(1)

    # Auto-click loop
    CALL_X_PERCENT = 0.75
    CALL_Y_PERCENT = 0.85
    canvas_rect = canvas.rect
    call_x = canvas_rect['width'] * CALL_X_PERCENT
    call_y = canvas_rect['height'] * CALL_Y_PERCENT

    print("[SUCCESS] Canvas found. Auto-clicking CALL every 5 seconds...")

    while True:
        try:
            driver.execute_script(
                "const canvas=arguments[0]; const x=arguments[1]; const y=arguments[2];"
                "canvas.dispatchEvent(new MouseEvent('mousedown',{clientX:x, clientY:y,bubbles:true}));"
                "canvas.dispatchEvent(new MouseEvent('mouseup',{clientX:x, clientY:y,bubbles:true}));",
                canvas, call_x, call_y
            )
            print("[CLICK] CALL clicked")
            time.sleep(5)
        except WebDriverException as e:
            print(f"[ERROR] WebDriver exception during click: {e}")
            time.sleep(5)

except Exception as e:
    print(f"[FATAL] Unexpected error: {e}")
finally:
    driver.quit()
