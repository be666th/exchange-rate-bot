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
from datetime import datetime
import time
import traceback

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

URL_BBL = "https://www.bangkokbank.com/th-th/personal/other-services/view-rates/foreign-exchange-rates"
TABLE_SELECTOR = "table.table-exchange-rate"  # ปรับได้หากธนาคารเปลี่ยนโครงสร้างหน้า


def safe_push_line(text: str):
    try:
        line_bot_api.push_message(GROUP_ID, TextSendMessage(text=text))
        print("📩 Sent LINE text message.")
    except Exception as e:
        print("❌ Failed to send LINE message:", repr(e))
        traceback.print_exc()


def upload_image(file_path, folder="exchange-rate") -> str:
    print("📤 Uploading image to Cloudinary...")
    try:
        response = cloudinary.uploader.upload(
            file_path,
            folder=folder,
            use_filename=True,
            unique_filename=False,
            overwrite=True
        )
        url = response["secure_url"]
        print(f"✅ Uploaded: {url}")
        return url
    except Exception as e:
        print("❌ Cloudinary upload failed:", repr(e))
        traceback.print_exc()
        raise


def _new_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    return driver


def capture_and_send():
    driver = None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_fullpage_name = f"bbl_fullpage_{ts}.png"
    table_img_name = f"bbl_exchange_{ts}.png"

    try:
        driver = _new_driver()

        # ✅ Retry loading page (3 ครั้ง)
        success = False
        for attempt in range(1, 4):
            try:
                print(f"🌐 Loading page (attempt {attempt}) → {URL_BBL}")
                driver.get(URL_BBL)
                success = True
                print("✅ Page loaded.")
                break
            except Exception as e:
                print(f"❌ Load failed (attempt {attempt}):", repr(e))
                time.sleep(3)

        if not success:
            driver.save_screenshot(f"load_fail_{ts}.png")
            safe_push_line("🛑 BBL page load failed after 3 retries.")
            return

        # ✅ บันทึก page_source ไว้ debug
        try:
            with open(f"page_source_{ts}.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("📄 page_source saved.")
        except Exception as e:
            print("⚠️ Could not write page_source:", repr(e))

        # ✅ รอให้ตารางโหลดและมองเห็นได้
        wait = WebDriverWait(driver, 35)
        table_el = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, TABLE_SELECTOR)))
        print("✅ Exchange table is visible.")

        # เลื่อนให้ตารางอยู่กลางหน้าจอ + ปรับ zoom เล็กน้อย
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", table_el)
            driver.execute_script("document.body.style.zoom='80%'")
            time.sleep(0.5)
        except Exception as e:
            print("⚠️ Scroll/zoom script failed:", repr(e))

        # ✅ แคปเต็มหน้า (เก็บไว้ debug)
        try:
            driver.save_screenshot(raw_fullpage_name)
            print(f"🖼️ Saved fullpage screenshot → {raw_fullpage_name}")
        except Exception as e:
            print("⚠️ Fullpage screenshot failed:", repr(e))

        # ✅ แคป “เฉพาะตาราง” อ่านง่าย
        try:
            table_el.screenshot(table_img_name)
            print(f"🖼️ Saved table screenshot → {table_img_name}")
        except Exception as e:
            print("❌ Element screenshot failed:", repr(e))
            # fallback: เซฟทั้งหน้าแทน
            driver.save_screenshot(table_img_name)
            print("↩️ Fallback to fullpage screenshot for table image.")

        # ✅ อัปโหลด Cloudinary
        image_url = upload_image(table_img_name, folder="exchange-rate")

        # ✅ ส่ง LINE พร้อมเวลาที่ไทย
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        msg = f"✅ Exchange Rate ({now_str}):\n{image_url}"
        safe_push_line(msg)

    except Exception as e:
        print("🛑 capture_and_send() failed:", repr(e))
        traceback.print_exc()
        safe_push_line("🛑 Exchange bot error occurred while capturing or sending image.")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# === FastAPI routes ===

@app.post("/")
async def webhook(request: Request):
    print("🔔 Received POST / webhook")
    try:
        body = await request.json()
        print("📥 Payload:", body)
    except Exception:
        print("📥 No/invalid JSON payload.")
    capture_and_send()
    return JSONResponse(content={"message": "OK"}, status_code=200)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/test-capture")
async def test_capture():
    capture_and_send()
    return {"status": "triggered"}

@app.get("/env")
async def env():
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
