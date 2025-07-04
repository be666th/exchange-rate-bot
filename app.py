# app.py (Production final refactor)

from dotenv import load_dotenv
load_dotenv()

import os
import cloudinary
import cloudinary.uploader
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from linebot import LineBotApi
from linebot.models import TextSendMessage

# ========== CONFIG ==========
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
)

# ========== FUNCTIONS ==========

def upload_image(file_path, folder="exchange-rate"):
    """Upload image to Cloudinary and return secure URL."""
    response = cloudinary.uploader.upload(
        file_path,
        folder=folder,
        use_filename=True,
        unique_filename=False,
        overwrite=True
    )
    print(f"✅ Uploaded to Cloudinary: {response['secure_url']}")
    return response["secure_url"]

def capture_and_send():
    """Capture BBL Exchange Rate page, upload to Cloudinary, and push LINE message."""

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)

    url_bbl = "https://www.bangkokbank.com/th-th/personal/other-services/view-rates/foreign-exchange-rates"
    driver.get(url_bbl)
    driver.implicitly_wait(5)

    driver.execute_script("document.body.style.zoom='75%'")

    bbl_img = "bbl_capture.png"
    driver.save_screenshot(bbl_img)
    driver.quit()

    print("✅ Screenshot captured.")

    # Upload to Cloudinary
    image_url = upload_image(bbl_img, folder="exchange-rate")

    # Push LINE message
    line_bot_api.push_message(
        GROUP_ID,
        TextSendMessage(text=f"✅ Exchange Rate capture uploaded: {image_url}")
    )
    print("✅ LINE push message sent.")

# ========== MAIN ==========
if __name__ == "__main__":
    print("✅ Exchange Rate Bot started (production mode)")
    capture_and_send()
