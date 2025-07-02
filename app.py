# app.py
from dotenv import load_dotenv
load_dotenv()

import os
import time
import schedule
import cloudinary
import cloudinary.uploader
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from linebot import LineBotApi
from linebot.models import TextSendMessage

# Load environment variables
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

def capture_exchange_rate():
    """Capture exchange rate page screenshot and return local file path"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    url = "https://www.bot.or.th/th/statistics/exchange-rate.html"
    driver.get(url)
    driver.implicitly_wait(5)

    screenshot_path = "/tmp/exchange_rate.png"
    driver.save_screenshot(screenshot_path)
    driver.quit()

    print(f"✅ Screenshot saved to {screenshot_path}")
    return screenshot_path

# Config Cloudinary
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
)

def upload_to_cloudinary(image_path):
    """Upload image to Cloudinary and return public URL"""
    print("🚀 Uploading image to Cloudinary...")
    response = cloudinary.uploader.upload(image_path)
    url = response.get('secure_url')
    print(f"✅ Uploaded to Cloudinary: {url}")
    return url
from linebot.models import ImageSendMessage

def job():
    print("🚀 Starting job: capture exchange rate and push LINE message")
    img_path = capture_exchange_rate()
    public_url = upload_to_cloudinary(img_path)
    message = ImageSendMessage(
        original_content_url=public_url,
        preview_image_url=public_url
    )
    line_bot_api.push_message(GROUP_ID, message)
    print("✅ Push image message sent.")



# Schedule at 08:31 every day
schedule.every().day.at("08:31").do(job)

if __name__ == "__main__":
    print("✅ Exchange Rate Bot started (Render worker mode)")
    while True:
        schedule.run_pending()
        time.sleep(30)
