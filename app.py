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


def capture_bbl_rate():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)

    driver.get("https://www.bangkokbank.com/th-TH/Personal/Other-Services/Rates/Foreign-Exchange-Rates")
    screenshot_path = "/tmp/bbl_rate.png"
    driver.save_screenshot(screenshot_path)
    driver.quit()
    return screenshot_path


def upload_to_cloudinary(image_path):
    response = cloudinary.uploader.upload(image_path)
    return response["secure_url"]


def send_line_image_message(image_url):
    image_message = ImageSendMessage(
        original_content_url=image_url,
        preview_image_url=image_url
    )
    line_bot_api.push_message(LINE_GROUP_ID, image_message)
