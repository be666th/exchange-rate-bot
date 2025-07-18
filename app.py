from fastapi import FastAPI
from dotenv import load_dotenv
import os
import time
import cloudinary
import cloudinary.uploader
from linebot import LineBotApi
from linebot.models import ImageSendMessage, TextSendMessage
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

load_dotenv()

app = FastAPI()

# Setup LINE
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
LINE_GROUP_ID = os.getenv("LINE_GROUP_ID")

# Setup Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def capture_and_send():
    url = "https://www.bangkokbank.com/th-TH/Personal/Other-Services/Rates-and-Calculators/Foreign-Exchange-Rates"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    screenshot_filename = f"bbl_capture_{timestamp}.png"

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    try:
        # รอจน popup ปรากฏ แล้วคลิกปุ่มยอมรับ
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'ยอมรับทั้งหมด')]"))
        ).click()

        time.sleep(1)
        driver.save_screenshot(screenshot_filename)
        print(f"✅ Screenshot saved: {screenshot_filename}")

        upload_result = cloudinary.uploader.upload(screenshot_filename, folder="exchange-rate/")
        image_url = upload_result["secure_url"]
        print(f"📤 Uploaded to Cloudinary: {image_url}")

        line_bot_api.push_message(LINE_GROUP_ID, [
            TextSendMessage(text=f"✅ Exchange Rate capture uploaded: {image_url}"),
            ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
        ])
        print("📨 LINE message sent.")

    finally:
        driver.quit()

@app.get("/")
def root():
    return {"message": "Exchange Rate Bot is alive"}

@app.get("/run")
def run_task():
    capture_and_send()
    return {"status": "completed"}
