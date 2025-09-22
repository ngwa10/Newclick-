import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

# --- Load .env ---
load_dotenv()
PO_EMAIL = os.getenv("POCKET_EMAIL")
PO_PASS = os.getenv("POCKET_PASS")

# --- Headless Chrome setup ---
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=chrome_options)

# --- Login ---
driver.get("https://pocketoption.com/en/login/")
time.sleep(2)

driver.find_element(By.NAME, "email").send_keys(PO_EMAIL)
driver.find_element(By.NAME, "password").send_keys(PO_PASS)
driver.find_element(By.XPATH, "//button[@type='submit']").click()
time.sleep(5)

# --- Navigate to demo quick trading ---
driver.get("https://m.pocketoption.com/en/cabinet/demo-quick-high-low/")
time.sleep(5)

# --- Canvas & CALL button coordinates ---
CALL_X_PERCENT = 0.75  # 75% width
CALL_Y_PERCENT = 0.85  # 85% height

canvas = driver.find_element(By.TAG_NAME, "canvas")
canvas_rect = canvas.rect

call_x = canvas_rect['width'] * CALL_X_PERCENT
call_y = canvas_rect['height'] * CALL_Y_PERCENT

print("Bot started: auto-clicking CALL every 5 seconds...")

# --- Auto-click loop ---
while True:
    driver.execute_script(
        "const canvas=arguments[0]; const x=arguments[1]; const y=arguments[2];"
        "canvas.dispatchEvent(new MouseEvent('mousedown',{clientX:x, clientY:y,bubbles:true}));"
        "canvas.dispatchEvent(new MouseEvent('mouseup',{clientX:x, clientY:y,bubbles:true}));",
        canvas, call_x, call_y
    )
    print("CALL clicked")
    time.sleep(5)
