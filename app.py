from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import cloudinary
import cloudinary.uploader
from linebot import LineBotApi
from linebot.models import TextSendMessage
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime

# ✅ Load env
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.getenv("GROUP_ID") or os.getenv("LINE_GROUP_ID")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

print("🧪 ENV loaded:")
print(f"  LINE_CHANNEL_ACCESS_TOKEN: {'✅' if LINE_CHANNEL_ACCESS_TOKEN else '❌'}")
print(f"  GROUP_ID: {GROUP_ID or '❌ (missing)'}")
print(f"  CLOUDINARY_CLOUD_NAME: {CLOUDINARY_CLOUD_NAME or '❌'}")

if not all([LINE_CHANNEL_ACCESS_TOKEN, GROUP_ID, CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
    raise RuntimeError("❌ Missing one or more required environment variables.")

# ✅ Setup clients
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
    url_bbl = "https://www.bangkokbank.com/th-th/personal/other-services/view-rates/foreign-exchange-rates"
    print("🌐 URL:", url_bbl)

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)

    # ✅ Retry loading page
    success = False
    for attempt in range(3):
        try:
            print(f"🔁 Attempt #{attempt+1} loading page...")
            driver.set_page_load_timeout(60)
            driver.get(url_bbl)
            print("✅ Page loaded.")
            success = True
            break
        except Exception as e:
            print(f"❌ Attempt #{attempt+1} failed:", e.__class__.__name__, ":", str(e))
            driver.save_screenshot(f"load_fail_{attempt+1}.png")
            time.sleep(3)

    if not success:
        print("🛑 Failed to load page after retries")
        driver.quit()
        return

    # ✅ Dump page source to file
    try:
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("📄 page_source.html saved ✅")
    except Exception as e:
        print("❌ Failed to write page_source.html:", e.__class__.__name__, str(e))

    # ✅ Wait for visible table
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-exchange-rate"))
        )
        print("✅ Table found (using .table-exchange-rate).")
    except Exception as e:
        print("❌ Table not found:", e.__class__.__name__, ":", str(e))
        driver.save_screenshot("table_not_found.png")
        driver.quit()
        return

    # ✅ Screenshot
    driver.execute_script("document.body.style.zoom='75%'")
    bbl_img = "bbl_capture.png"
    driver.save_screenshot(bbl_img)
    driver.quit()
    print("✅ Screenshot captured.")

    # ✅ Upload to Cloudinary
    image_url = upload_image(bbl_img, folder="exchange-rate")

    # ✅ Send to LINE
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    message = f"✅ Exchange Rate ({now}):\n{image_url}"
    line_bot_api.push_message(GROUP_ID, TextSendMessage(text=message))
    print("✅ LINE message sent.")




# === FastAPI routes ===

@app.post("/")
async def webhook(request: Request):
    print("🔔 Received POST / webhook")
    body = await request.json()
    print("📥 Payload:", body)
    capture_and_send()
    return JSONResponse(content={"message": "OK"}, status_code=200)

@app.get("/health")
async def health():
    return {"status": "ok"}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
