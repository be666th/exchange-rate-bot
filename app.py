from fastapi import FastAPI
from dotenv import load_dotenv
import os
import time
import cloudinary
import cloudinary.uploader
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from linebot import LineBotApi
from linebot.models import ImageSendMessage

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_GROUP_ID = os.getenv("LINE_GROUP_ID")
URL = "https://www.bangkokbank.com/th-TH/Personal/Other-Services/View-Rates/Foreign-Exchange-Rates"


app = FastAPI()

def capture_and_send():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--force-device-scale-factor=1")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(URL)

    # ✅ รอให้ปุ่ม "ยอมรับทั้งหมด" แสดงก่อนคลิก
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button#onetrust-accept-btn-handler"))
        ).click()
    except:
        pass  # ถ้าไม่เจอปุ่ม ก็ข้ามไป

    time.sleep(3)  # รอโหลดเนื้อหา

    # ✅ ซูมออก 75% ก่อน capture
    driver.execute_script("document.body.style.zoom='75%'")

    screenshot_path = "bbl_capture.png"
    driver.save_screenshot(screenshot_path)
    driver.quit()

    # ✅ อัปโหลดขึ้น Cloudinary
    url = upload_to_cloudinary(screenshot_path)

    # ✅ ส่ง LINE
    send_line_image_message(url)

def upload_to_cloudinary(image_path: str) -> str:
    response = cloudinary.uploader.upload(image_path)
    return response["secure_url"]

def send_line_image_message(image_url: str):
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    image_message = ImageSendMessage(
        original_content_url=image_url,
        preview_image_url=image_url
    )
    line_bot_api.push_message(LINE_GROUP_ID, image_message)

@app.get("/")
def root():
    return {"message": "Exchange Rate Bot is live."}

@app.get("/run")
def run_bot():
    capture_and_send()
    return {"message": "Capture and send completed."}
