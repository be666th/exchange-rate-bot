from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import traceback
import cloudinary
import cloudinary.uploader
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

load_dotenv()

app = FastAPI()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def upload_image(file_path, folder="exchange-rate"):
    """Upload image to Cloudinary and return secure URL"""
    response = cloudinary.uploader.upload(
        file_path,
        folder=folder,
        use_filename=True,
        unique_filename=False,
        overwrite=True
    )
    print(f"✅ Uploaded to Cloudinary: {response['secure_url']}")
    return response["secure_url"]

def upload_debug(file_path):
    """Upload debug file to Cloudinary under exchange-rate/debug"""
    try:
        return upload_image(file_path, folder="exchange-rate/debug")
    except Exception as e:
        print(f"❌ Failed to upload debug file {file_path}: {e}")
        return None

def capture_and_send():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bbl_img = f"bbl_capture_{ts}.png"
    page_src_file = f"page_source_{ts}.html"

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        url_bbl = "https://www.bangkokbank.com/th-th/personal/other-services/view-rates/foreign-exchange-rates"
        driver.get(url_bbl)
        driver.implicitly_wait(5)
        driver.execute_script("document.body.style.zoom='75%'")

        # Save page source for debugging
        with open(page_src_file, "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        # Try waiting for table to appear
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-exchange-rate"))
            )
        except Exception as e:
            print("⚠️ Could not locate table element:", e)

        driver.save_screenshot(bbl_img)
        print("✅ Screenshot captured.")

        image_url = upload_image(bbl_img, folder="exchange-rate")

        line_bot_api.push_message(
            GROUP_ID,
            TextSendMessage(text=f"✅ Exchange Rate capture uploaded: {image_url}")
        )
        print("✅ LINE push message sent.")

    except Exception as e:
        print("🛑 Error in capture_and_send:", e)
        traceback.print_exc()

        # Save and upload debug files
        debug_links = []
        try:
            if driver:
                driver.save_screenshot(bbl_img)
                link_img = upload_debug(bbl_img)
                if link_img:
                    debug_links.append(f"Screenshot: {link_img}")

            if os.path.exists(page_src_file):
                link_html = upload_debug(page_src_file)
                if link_html:
                    debug_links.append(f"Page source: {link_html}")

            if debug_links:
                debug_msg = "🛑 Capture failed. Debug files:\n" + "\n".join(debug_links)
                line_bot_api.push_message(GROUP_ID, TextSendMessage(text=debug_msg))
        except Exception as ex:
            print("❌ Failed to handle debug upload:", ex)

    finally:
        if driver:
            driver.quit()

@app.post("/")
async def webhook(request: Request):
    try:
        body = await request.json()
        print("🔔 Received event:", body)
    except:
        pass
    capture_and_send()
    return JSONResponse(content={"message": "OK"}, status_code=200)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
