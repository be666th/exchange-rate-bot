from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os, time, traceback, pathlib
from datetime import datetime
import pytz  # ✅ ใช้เวลา Asia/Bangkok

import cloudinary
import cloudinary.uploader
from PIL import Image  # ✅ ขยาย/บีบอัด JPEG

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from linebot import LineBotApi
from linebot.models import TextSendMessage, ImageSendMessage
from linebot.exceptions import LineBotApiError

# ===== ENV & Clients =====
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.getenv("GROUP_ID") or os.getenv("LINE_GROUP_ID")
CAPTURE_MODE = "JPY"  # 🔒 บังคับ JPY ตามสเปกข้อความ

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

app = FastAPI()
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

URL_BBL = "https://www.bangkokbank.com/th-th/personal/other-services/view-rates/foreign-exchange-rates"

# -------- helpers --------
def safe_push_line(text: str) -> bool:
    try:
        line_bot_api.push_message(GROUP_ID, TextSendMessage(text=text))
        print("📩 LINE text message sent.")
        return True
    except LineBotApiError as e:
        print("❌ LineBotApiError status:", getattr(e, "status_code", None))
        err = getattr(e, "error", None)
        if err:
            print("   message:", getattr(err, "message", None))
            if hasattr(err, "details"):
                for d in err.details:
                    print(f"   - {d.property}: {d.message}")
        else:
            print("   raw exception:", repr(e))
        return False
    except Exception as e:
        print("❌ LINE push failed (generic):", repr(e))
        return False

def safe_push_image(image_url: str) -> bool:
    """ส่งรูปภาพเข้า LINE group ผ่าน ImageSendMessage"""
    try:
        line_bot_api.push_message(
            GROUP_ID,
            ImageSendMessage(
                original_content_url=image_url,
                preview_image_url=image_url
            )
        )
        print("🖼️ LINE image sent:", image_url)
        return True
    except LineBotApiError as e:
        print("❌ LINE image push error:", getattr(e, "status_code", None), repr(e))
        return False
    except Exception as e:
        print("❌ LINE image push failed (generic):", repr(e))
        return False

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
    opt.add_argument("--window-size=2880,1620")
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

def find_jpy_row(driver):
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        for r in rows:
            if "JPY" in (r.text or "").upper():
                return r
        return driver.find_element(By.XPATH, "//table//tr[td[contains(translate(., 'jpy','JPY'),'JPY')]]")
    except Exception:
        return None

def extract_jpy_rates(jpy_row) -> tuple[str, str]:
    """ดึงอัตราซื้อ (TT Buying) และขาย (TT Selling) จากแถว JPY
    คืนค่า (buying_rate, selling_rate) เป็น string เช่น ('19.76', '20.84')
    """
    try:
        cells = jpy_row.find_elements(By.TAG_NAME, "td")
        # กรองเฉพาะ cell ที่มีตัวเลขอัตราแลกเปลี่ยน (มีจุดทศนิยม)
        numbers = []
        for cell in cells:
            txt = (cell.text or "").strip().replace(",", "")
            try:
                val = float(txt)
                if val > 0:
                    numbers.append(txt)
            except ValueError:
                pass
        # Bangkok Bank: col 0=TT Buying, col 1=TT Selling (หรือ Buying/Selling คู่แรก)
        if len(numbers) >= 2:
            return numbers[0], numbers[-1]
        elif len(numbers) == 1:
            return numbers[0], numbers[0]
    except Exception as e:
        print(f"⚠️ extract_jpy_rates failed: {e}")
    return "", ""

# --- image utils ---
from PIL import Image

def to_jpeg_optimized(src_path: str, min_quality=75, target_mb=8) -> str:
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
            quality -= 5
    except Exception as e:
        print(f"⚠️ JPEG optimize failed: {e}")
        return src_path
    return dst_path

def resize_image(path, scale=1.5) -> str:
    try:
        img = Image.open(path)
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)
        tmp_path = str(pathlib.Path(path).with_name(pathlib.Path(path).stem + "_scaled.png"))
        img.save(tmp_path)
        print(f"🖼️ Image resized to {new_size}")
        return to_jpeg_optimized(tmp_path)
    except Exception as e:
        print(f"⚠️ Failed to resize image {path}: {e}")
        return to_jpeg_optimized(path)

# -------- main flow --------
def capture_and_send():
    tz_bkk = pytz.timezone("Asia/Bangkok")
    now_bkk = datetime.now(tz_bkk).strftime("%Y-%m-%d %H:%M")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_png = f"full_{ts}.png"
    table_png = f"bbl_exchange_{ts}.png"
    page_src = f"page_source_{ts}.html"

    driver = None
    jpy_captured = False
    fullpage_url = None
    jpy_image_url = None
    jpy_buying = ""
    jpy_selling = ""

    try:
        driver = new_driver()
        driver.get(URL_BBL)
        dismiss_cookies(driver)
        driver.execute_script("document.body.style.zoom='110%'")
        time.sleep(0.6)

        # debug: page source (อัปขึ้นแต่ไม่ใส่ในข้อความ LINE)
        try:
            with open(page_src, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            _ = upload_debug(page_src)
        except Exception as e:
            print("⚠️ save/upload page_source failed:", e)

        # หา table + fullpage debug (อันนี้จะใส่ลิงก์ในข้อความ LINE)
        table_el = wait_exchange_table(driver, timeout=45)
        try:
            driver.save_screenshot(full_png)
            fullpage_url = upload_debug(full_png)
        except Exception:
            pass

        if table_el:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", table_el)
            time.sleep(0.25)
            jpy_row = find_jpy_row(driver)
            if jpy_row:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", jpy_row)
                    time.sleep(0.2)
                    # ดึงตัวเลขอัตราแลกเปลี่ยนก่อน screenshot
                    jpy_buying, jpy_selling = extract_jpy_rates(jpy_row)
                    print(f"💱 JPY rates — buying: {jpy_buying}, selling: {jpy_selling}")
                    jpy_row.screenshot(table_png)
                    # resize + optimize เป็น JPEG แล้ว upload ขึ้น Cloudinary
                    scaled_path = resize_image(table_png, scale=1.5)
                    jpy_image_url = upload_cloudinary(scaled_path, folder="exchange-rate")
                    print(f"✅ JPY image uploaded: {jpy_image_url}")
                    jpy_captured = True
                except Exception as e:
                    print(f"⚠️ JPY capture/upload failed: {e}")
                    jpy_captured = False
            else:
                jpy_captured = False
        else:
            jpy_captured = False

    except Exception as e:
        print("🛑 capture_and_send error:", repr(e))
        traceback.print_exc()
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # ==== Message 1: รวม text ทุกอย่างในข้อความเดียว ====
    image_url = jpy_image_url or fullpage_url or ""
    lines = [f"📊 Exchange Rate ({now_bkk} +7UTC)"]
    if image_url:
        lines.append(f"🔗 {image_url}")
    if jpy_buying:
        lines.append(f"💱 JPY {jpy_buying}")

    safe_push_line("\n".join(lines))

    # ==== Message 2: รูปภาพ JPY ====
    if jpy_image_url:
        safe_push_image(jpy_image_url)
    elif fullpage_url:
        safe_push_image(fullpage_url)

# ===== FastAPI routes =====
@app.post("/")
async def webhook(request: Request):
    # รับ LINE webhook event แล้วตอบ 200 OK เฉยๆ
    # ไม่ trigger capture_and_send() เพื่อไม่ให้ bot ตอบกลับทุกข้อความในกลุ่ม
    try:
        body = await request.json()
        print("🔔 Received event (ignored):", body)
    except Exception:
        pass
    return JSONResponse(content={"message": "OK"}, status_code=200)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/test-capture")
async def test_capture():
    capture_and_send()
    return {"status": "triggered"}

# Diagnostics (คงไว้ใช้เวลามีปัญหา)
@app.get("/line-test")
async def line_test():
    ok = safe_push_line("🔔 LINE connectivity test from Exchange Rate Bot")
    return {"ok": ok}

@app.get("/env-check")
async def env_check():
    return {
        "LINE_TOKEN": bool(os.getenv("LINE_CHANNEL_ACCESS_TOKEN")),
        "GROUP_ID_prefix": (os.getenv("GROUP_ID") or os.getenv("LINE_GROUP_ID") or "")[:3],
        "CAPTURE_MODE": CAPTURE_MODE,
        "TZ": "Asia/Bangkok (+7UTC)"
    }
