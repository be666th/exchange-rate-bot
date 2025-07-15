from fastapi import FastAPI
import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from linebot import LineBotApi
from linebot.models import ImageSendMessage

load_dotenv()

app = FastAPI()

# LINE config
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_GROUP_ID = os.getenv("LINE_GROUP_ID")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

# Cloudinary config
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


@app.get("/")
def read_root():
    return {"message": "Exchange Rate Bot is live."}


@app.get("/capture-and-send")
def capture_and_send():
    image_path = capture_bbl_rate()
    url = upload_to_cloudinary(image_path)
    send_line_image_message(url)
    return {"status": "sent", "image_url": url}

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def capture_and_send():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1600, 1400)

    try:
        driver.get("https://www.bangkokbank.com/th-TH/Personal/Other-Services/Rates/Foreign-Exchange-Rates")

        # รอโหลดหน้าเบื้องต้น
        time.sleep(3)

        # คลิกปุ่ม "ยอมรับทั้งหมด"
        try:
            accept_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "ยอมรับทั้งหมด")]'))
            )
            accept_button.click()
        except:
            print("Cookie banner not found, continue...")

        # รอตารางแสดงอัตราแลกเปลี่ยนโหลด
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )

        screenshot_path = "screenshot.png"
        driver.save_screenshot(screenshot_path)

        image_url = upload_to_cloudinary(screenshot_path)
        send_line_image_message(image_url)

    finally:
        driver.quit()


def upload_to_cloudinary(image_path):
    response = cloudinary.uploader.upload(image_path)
    return response["secure_url"]


def send_line_image_message(image_url):
    image_message = ImageSendMessage(
        original_content_url=image_url,
        preview_image_url=image_url
    )
    line_bot_api.push_message(LINE_GROUP_ID, image_message)
