from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os, time, traceback
from datetime import datetime
import pathlib

import cloudinary
import cloudinary.uploader
from PIL import Image  # ✅ สำหรับแปลง/บีบอัดรูป

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from linebot import LineBotApi
from linebot.models import TextSendMessage

# ===== ENV & Clients =====
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.getenv("GROUP_ID") or os.getenv("LINE_GROUP_ID")

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

app = FastAPI()
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

URL_BBL = "https://www.bangkokbank.com/th-th/personal/other-services/view-rates/foreign-exchange-rates"

# -------- helpers --------
def safe_push_line(text: str):
    try:
        line_bot_api.push_message(GROUP_ID, TextSendMessage(text=text))
        print("📩 LINE message sent.")
    except Exception as e:
        print("❌ LINE push failed:", repr(e))
        traceback.print_exc()

def upload_cloudinary(path: str, folder="exchange-rate") -> str:
    resp = cloudinary.uploader.upload(
        path, folder=folder, use_filename=True, unique_filename=False, overwrite=True
    )
    return resp["secure_url"]

def upload_debug(path: str) -> str | None:
    try:
        return upload_cloudinary(path, folder="exchange-rate/debug")
    except Exception as e:
        print(f"⚠️ Upload debug failed for {path}: {e}")
        return None

def new_driver() -> webdriver.Chrome:
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--window-size=2880,1620")  # ✅ ใหญ่ขึ้นเพื่อความคม
    opt.add_argument("--lang=th-TH")
    opt.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    drv = webdriver.Chrome(options=opt)
    drv.set_page_load_timeout(60)
    return drv

def dismiss_cookies(driver):
    for sel in [
        "#onetrust-accept-btn-handler",
        "button[aria-label='ยอมรับทั้งหมด']",
        "button[aria-label='Accept All']",
        ".ot-sdk-container #onetrust-accept-btn-handler",
    ]:
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, sel)
            if btns:
                btns[0].click()
                time.sleep(0.2)
                break
        except Exception:
            pass

def wait_exchange_table(driver, timeout=45):
    wait = WebDriverWait(driver, timeout)
    candidates = [
        "table.table-exchange-rate",
        "table[class*='exchange']",
        "section table",
    ]
    table = None
    for css in candidates:
        try:
            table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
            rows_ok = WebDriverWait(driver, 10).until(
                lambda d: len(table.find_elements(By.CSS_SELECTOR, "tbody tr")) > 0
            )
            if rows_ok:
                return table
        except Exception:
            table = None
    try:
        table = wait.until(
            lambda d: next(
                (t for t in d.find_elements(By.TAG_NAME, "table") if "JPY" in (t.text or "")),
                None
            )
        )
    except Exception:
        table = None
    return table

# --- image utils ---
def to_jpeg_optimized(src_path: str, min_quality=75, target_mb=8) -> str:
    """
    เปิดไฟล์ src_path (PNG/JPG) -> แปลงเป็น JPEG + optimize, ลดคุณภาพลงอัตโนมัติถ้าไฟล์ใหญ่เกิน target_mb
    Return: path ใหม่ (นามสกุล .jpg)
    """
    dst_path = str(pathlib.Path(src_path).with_suffix(".jpg"))
    try:
        img = Image.open(src_path).convert("RGB")
        quality = 90
        while True:
            img.save(dst_path, format="JPEG", optimize=True, quality=quality)
            size_mb = os.path.getsize(dst_path) / (1024 * 1024)
            print(f"🗜️ JPEG saved quality={quality}, size={size_mb:.2f} MB")
            if size_mb <= target_mb or quality <= min_quality:
                break
            quality -= 5  # ลดทีละ 5 จนกว่าจะต่ำกว่า target หรือถึง min_quality
    except Exception as e:
        print(f"⚠️ JPEG optimize failed: {e}")
        # ถ้าแปลงไม่สำเร็จ ให้ใช้ไฟล์เดิม
        return src_path
    return dst_path

def resize_image(path, scale=1.5) -> str:
    """ขยายภาพ แล้วส่งต่อเข้า to_jpeg_optimized()"""
    try:
        img = Image.open(path)
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)
        tmp_path = str(pathlib.Path(path).with_name(pathlib.Path(path).stem + "_scaled.png"))
        img.save(tmp_path)  # เซฟชั่วคราวเป็น PNG ก่อน
        print(f"🖼️ Image resized to {new_size}")
        return to_jpeg_optimized(tmp_path)
    except Exception as e:
        print(f"⚠️ Failed to resize image {path}: {e}")
        return to_jpeg_optimized(path)

# -------- main flow --------
def capture_and_send():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_png = f"full_{ts}.png"
    table_png = f"bbl_exchange_{ts}.png"
    page_src = f"page_source_{ts}.html"

    driver = None
    message_lines = []
    image_url = None
    debug_links = []

    try:
        driver = new_driver()
        driver.get(URL_BBL)
        dismiss_cookies(driver)
        driver.execute_script("document.body.style.zoom='110%'")  # ✅ ซูมให้ตัวใหญ่ขึ้น
        time.sleep(0.6)

        # save page source
        try:
            with open(page_src, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            link_src = upload_debug(page_src)
            if link_src:
                debug_links.append(f"Page source: {link_src}")
        except Exception as e:
            print("⚠️ save/upload page_source failed:", e)

        # find table
        table_el = wait_exchange_table(driver, timeout=45)

        # fullpage debug
        try:
            driver.save_screenshot(full_png)
            link_full = upload_debug(full_png)
            if link_full:
                debug_links.append(f"Fullpage: {link_full}")
        except Exception:
            pass

        if table_el:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", table_el)
            time.sleep(0.3)
            try:
                table_el.screenshot(table_png)
            except Exception:
                driver.save_screenshot(table_png)
            # ✅ ขยาย + แปลงเป็น JPEG ที่บีบอัดเหมาะกับ LINE
            table_jpg = resize_image(table_png, scale=1.5)
            image_url = upload_cloudinary(table_jpg, folder="exchange-rate")
            message_lines.append("✅ Exchange Rate: จับตารางสำเร็จ")
        else:
            driver.save_screenshot(table_png)
            table_jpg = resize_image(table_png, scale=1.5)
            image_url = upload_cloudinary(table_jpg, folder="exchange-rate")
            message_lines.append("⚠️ ไม่พบตาราง → ส่งภาพเต็มหน้าแทน")

    except Exception as e:
        print("🛑 capture_and_send error:", repr(e))
        traceback.print_exc()
        message_lines.append("🛑 เกิดข้อผิดพลาดระหว่างจับภาพ/ส่งภาพ")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    now_th = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = [f"Exchange Rate ({now_th})"]
    msg.extend(message_lines)
    if image_url:
        msg.append(image_url)
    if debug_links:
        msg.append("🔎 Debug:")
        msg.extend(debug_links)

    safe_push_line("\n".join(msg))

# ===== FastAPI routes =====
@app.post("/")
async def webhook(request: Request):
    try:
        body = await request.json()
        print("🔔 Received event:", body)
    except Exception:
        pass
    capture_and_send()
    return JSONResponse(content={"message": "OK"}, status_code=200)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/test-capture")
async def test_capture():
    capture_and_send()
    return {"status": "triggered"}
