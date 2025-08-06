from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import cloudinary
import cloudinary.uploader
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
from linebot import LineBotApi
from linebot.models import TextSendMessage
import traceback
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ✅ Load .env
load_dotenv()

# ✅ Load environment variables with fallback
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.getenv("GROUP_ID") or os.getenv("LINE_GROUP_ID")  # ✅ fallback
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# ✅ Debug log
print("🧪 ENV loaded:")
print(f"  LINE_CHANNEL_ACCESS_TOKEN: {'✅' if LINE_CHANNEL_ACCESS_TOKEN else '❌'}")
print(f"  GROUP_ID: {GROUP_ID or '❌ (missing)'}")
print(f"  CLOUDINARY_CLOUD_NAME: {CLOUDINARY_CLOUD_NAME or '❌'}")

# ✅ Validate required env
if not all([LINE_CHANNEL_ACCESS_TOKEN, GROUP_ID, CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
    raise RuntimeError("❌ Missing one or more required environment variables. Check your .env or GitHub secrets.")

# ✅ Setup
app = FastAPI()
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

def upload_image(file_path, folder="exchange-rate"):
    print("📤 Uploading image to Cloudinary...")
    response = cloudinary.uploader.upload(
        file_path,
        folder=folder,
        use_filename=True,
        unique_filename=False,
        overwrite=True
    )
    print(f"✅ Uploaded: {response['secure_url']}")
    return response["secure_url"]

def capture_and_send():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    url_bbl = "https://www.bangkokbank.com/th-th/personal/other-services/view-rates/foreign-exchange-rates"
    driver.get(url_bbl)

    # ✅ รอให้ตาราง exchange rate โหลดสำเร็จ
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-exchange-rate"))
        )
        print("✅ Table loaded.")
    except Exception as e:
        print("❌ Table not loaded:", e)

    driver.execute_script("document.body.style.zoom='75%'")
    bbl_img = "bbl_capture.png"
    driver.save_screenshot(bbl_img)
    driver.quit()

    print("✅ Screenshot captured.")
    image_url = upload_image(bbl_img, folder="exchange-rate")
    line_bot_api.push_message(
        GROUP_ID,
        TextSendMessage(text=f"✅ Exchange Rate capture uploaded: {image_url}")
    )
    print("✅ LINE push message sent.")
            return

        except Exception as e:
            print(f"❌ Error on attempt #{attempt + 1}:")
            traceback.print_exc()

            if 'driver' in locals():
                driver.quit()

            if attempt >= retry:
                print("🛑 All retries failed.")
                return
            else:
                time.sleep(5)
                attempt += 1

# === FastAPI Routes ===

@app.post("/")
async def webhook(request: Request):
    print("🔔 Received POST / webhook")
    body = await request.json()
    print("📥 Payload:", body)
    capture_and_send()
    return JSONResponse(content={"message": "OK"}, status_code=200)

@app.get("/test")
async def test():
    return {
        "status": "ok",
        "env": {
            "LINE_CHANNEL_ACCESS_TOKEN": bool(LINE_CHANNEL_ACCESS_TOKEN),
            "GROUP_ID": GROUP_ID or "❌ missing",
            "CLOUDINARY_CLOUD_NAME": CLOUDINARY_CLOUD_NAME or "❌ missing"
        }
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

