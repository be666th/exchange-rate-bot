from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os, time
from datetime import datetime
import pytz  # ✅ ใช้เวลา Asia/Bangkok

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from linebot import LineBotApi
from linebot.models import TextSendMessage, FlexSendMessage
from linebot.exceptions import LineBotApiError

# ===== ENV & Clients =====
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.getenv("GROUP_ID") or os.getenv("LINE_GROUP_ID")
app = FastAPI()
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

URL_BBL = "https://www.bangkokbank.com/th-th/personal/other-services/view-rates/foreign-exchange-rates"
URL_SUPERRICH = "https://www.superrichthailand.com/#!/th"                 # Super Rich สีเขียว
URL_SUPERRICH_ORANGE = "https://superrich.co.th/currency.php"             # Super Rich สีส้ม

# -------- Brand colors (ใช้ทั้งหัวข้อ/บรรทัดคำอธิบาย/ลิงก์ ตาม mockup ที่ตกลงกัน) --------
COLOR_BBL_LABEL = "#666666"        # BBL: หัวข้อ/คำอธิบายเป็นสีเทากลาง
COLOR_BBL_LINK = "#1976D2"         # BBL: ลิงก์เป็นสีฟ้า
COLOR_SR_GREEN = "#1E8E3E"         # Super Rich สีเขียว: ทั้งหัวข้อ/คำอธิบาย/ลิงก์ เป็นสีเขียว
COLOR_SR_ORANGE = "#F57C00"        # Super Rich สีส้ม: ทั้งหัวข้อ/คำอธิบาย/ลิงก์ เป็นสีส้ม

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

def safe_push_flex(alt_text: str, contents: dict) -> bool:
    """ส่ง LINE Flex Message (การ์ด) แทน text ธรรมดา"""
    try:
        line_bot_api.push_message(GROUP_ID, FlexSendMessage(alt_text=alt_text, contents=contents))
        print("📩 LINE flex message sent.")
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

# -------- Super Rich สีเขียว scraper --------
def scrape_superrich_jpy() -> str:
    """ดึงอัตราซื้อ JPY จาก Super Rich Thailand (สีเขียว)
    รูปแบบในเว็บ: '0.2035 THB = 1 JPY' → คืนค่า '0.2035'
    """
    driver = None
    try:
        driver = new_driver()
        driver.get(URL_SUPERRICH)
        wait = WebDriverWait(driver, 45)

        # รอให้ตาราง/แถวที่มี JPY โหลดเสร็จ
        jpy_el = wait.until(
            lambda d: next(
                (el for el in d.find_elements(By.XPATH, "//*[contains(text(),'JPY')]")
                 if el.text.strip()),
                None
            )
        )

        # เดิน DOM ขึ้นไปหา row แม่ แล้วหาตัวเลขอัตราซื้อ
        # Super Rich แสดง "0.2035 THB = 1 JPY" — ดึงตัวเลขแรกในแถว
        row = jpy_el
        for _ in range(5):
            parent = row.find_element(By.XPATH, "..")
            siblings = parent.find_elements(By.XPATH, ".//*")
            for el in siblings:
                txt = (el.text or "").strip().replace(",", "")
                try:
                    val = float(txt)
                    if 0 < val < 10:  # อัตรา JPY/THB อยู่ในช่วง ~0.2x
                        print(f"💱 Super Rich (เขียว) JPY buying: {txt}")
                        return txt
                except ValueError:
                    pass
            row = parent

        print("⚠️ Super Rich (เขียว) JPY rate not found in DOM walk")
        return ""

    except Exception as e:
        print(f"⚠️ scrape_superrich_jpy failed: {e}")
        return ""
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# -------- Super Rich สีส้ม scraper (ใหม่) --------
def scrape_superrich_orange_jpy() -> str:
    """ดึงอัตราซื้อ JPY จาก Super Rich (สีส้ม, superrich.co.th)

    ⚠️ หน้าเว็บนี้โหลดตารางอัตราด้วย JS/AJAX ไม่มี CSS class ตายตัวที่ยืนยันได้จากภายนอก
    (ไม่มี headless browser ให้ตรวจสอบตอนเขียนโค้ดนี้) ใช้วิธี wait หาแถวที่มีคำว่า "JPY"
    แล้วดึงตัวเลขในแถวเดียวกันแบบเดียวกับ Super Rich สีเขียว
    ควรทดสอบจริงด้วย `python runner.py superrich_orange` — ถ้าไม่เจอ/ค่าไม่สมเหตุสมผล
    (เช่น เว็บนี้อาจ quote JPY ต่อ 100 หน่วยแทนที่จะเป็นต่อ 1 หน่วย) ให้ปรับช่วงตัวเลขหรือ selector ตรงนี้
    """
    driver = None
    try:
        driver = new_driver()
        driver.get(URL_SUPERRICH_ORANGE)
        wait = WebDriverWait(driver, 45)

        jpy_row = wait.until(
            lambda d: next(
                (row for row in d.find_elements(By.XPATH, "//tr[.//*[contains(text(),'JPY')]]")
                 if row.text.strip()),
                None
            )
        )

        cells = jpy_row.find_elements(By.XPATH, ".//td | .//th | .//div | .//span")
        numbers = []
        for cell in cells:
            txt = (cell.text or "").strip().replace(",", "")
            try:
                val = float(txt)
                if val > 0:
                    numbers.append(txt)
            except ValueError:
                pass

        if numbers:
            buying = numbers[0]
            print(f"💱 Super Rich (ส้ม) JPY buying (raw, ยังไม่ยืนยันหน่วย): {buying} | full row text: {jpy_row.text!r}")
            return buying

        print(f"⚠️ Super Rich (ส้ม) JPY rate not found — row text: {jpy_row.text!r}")
        return ""

    except Exception as e:
        print(f"⚠️ scrape_superrich_orange_jpy failed: {e}")
        return ""
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# -------- Static display URLs --------
BBL_URL_DISPLAY = "https://www.bangkokbank.com/th-TH/Personal/Other-Services/View-Rates/Foreign-Exchange-Rates"
SR_URL_DISPLAY = "https://www.superrichthailand.com/#!/th"        # Super Rich สีเขียว
SR_ORANGE_URL_DISPLAY = "https://superrich.co.th"                 # Super Rich สีส้ม

def _bkk_now() -> str:
    return datetime.now(pytz.timezone("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M")

# -------- BBL scraper (rate only, no screenshot) --------
def _scrape_bbl_jpy_once() -> str:
    """scrape BBL ครั้งเดียว — ใช้เรียกซ้ำจาก scrape_bbl_jpy()"""
    driver = None
    try:
        driver = new_driver()
        driver.get(URL_BBL)
        dismiss_cookies(driver)
        driver.execute_script("document.body.style.zoom='110%'")
        time.sleep(0.6)
        table_el = wait_exchange_table(driver, timeout=45)
        if not table_el:
            print("⚠️ BBL exchange table not found")
            return ""
        jpy_row = find_jpy_row(driver)
        if not jpy_row:
            print("⚠️ JPY row not found in BBL table")
            return ""
        buying, _ = extract_jpy_rates(jpy_row)
        print(f"💱 BBL JPY buying: {buying}")
        return buying
    except Exception as e:
        print(f"⚠️ scrape_bbl_jpy failed: {e}")
        return ""
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass

def scrape_bbl_jpy() -> str:
    """ดึงอัตราซื้อ JPY จาก Bangkok Bank — retry 1 ครั้งถ้าครั้งแรกได้ค่าว่าง"""
    rate = _scrape_bbl_jpy_once()
    if not rate:
        print("🔄 BBL retry attempt 2...")
        rate = _scrape_bbl_jpy_once()
    return rate

# -------- Flex Message bubble builder --------
def _build_rate_bubble(label: str, desc: str, rate: str, link_label: str, link_url: str,
                        header_color: str, link_color: str) -> dict:
    """สร้าง LINE Flex bubble ตาม mockup: หัวข้อ/คำอธิบาย -> ตัวเลขอัตราตัวใหญ่ -> ลิงก์กดได้"""
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "text",
                    "text": label,
                    "size": "sm",
                    "weight": "bold",
                    "color": header_color,
                },
                {
                    "type": "text",
                    "text": desc,
                    "size": "sm",
                    "color": header_color,
                    "wrap": True,
                },
                {
                    "type": "text",
                    "text": f"💱 JPY {rate if rate else 'N/A'}",
                    "size": "3xl",
                    "weight": "bold",
                    "margin": "md",
                    "wrap": True,
                },
                {
                    "type": "text",
                    "text": link_label,
                    "size": "md",
                    "weight": "bold",
                    "color": link_color,
                    "decoration": "underline",
                    "margin": "md",
                    "wrap": True,
                    "action": {
                        "type": "uri",
                        "label": link_label[:20],
                        "uri": link_url,
                    },
                },
            ],
        },
    }

# -------- 4 send functions --------
def send_bbl():
    rate = scrape_bbl_jpy()
    bubble = _build_rate_bubble(
        label="BBL",
        desc=f"📊 ({_bkk_now()}) -- อัตราแลกเปลี่ยนธนาคารกรุงเทพ",
        rate=rate,
        link_label="BBL Rate",
        link_url=BBL_URL_DISPLAY,
        header_color=COLOR_BBL_LABEL,
        link_color=COLOR_BBL_LINK,
    )
    safe_push_flex(f"BBL JPY {rate}", bubble)

def send_superrich():
    """Super Rich สีเขียว"""
    rate = scrape_superrich_jpy()
    bubble = _build_rate_bubble(
        label="SUPER RICH สีเขียว",
        desc=f"📊 ({_bkk_now()}) -- อัตราแลกเปลี่ยนซุปเปอร์ริช สีเขียว",
        rate=rate,
        link_label="SUPER RICH สีเขียว Rate",
        link_url=SR_URL_DISPLAY,
        header_color=COLOR_SR_GREEN,
        link_color=COLOR_SR_GREEN,
    )
    safe_push_flex(f"SUPER RICH สีเขียว JPY {rate}", bubble)

def send_superrich_orange():
    """Super Rich สีส้ม"""
    rate = scrape_superrich_orange_jpy()
    bubble = _build_rate_bubble(
        label="SUPER RICH สีส้ม",
        desc=f"📊 ({_bkk_now()}) -- อัตราแลกเปลี่ยนซุปเปอร์ริช สีส้ม",
        rate=rate,
        link_label="SUPER RICH สีส้ม Rate",
        link_url=SR_ORANGE_URL_DISPLAY,
        header_color=COLOR_SR_ORANGE,
        link_color=COLOR_SR_ORANGE,
    )
    safe_push_flex(f"SUPER RICH สีส้ม JPY {rate}", bubble)

def send_combined():
    """BBL + Super Rich สีเขียว + Super Rich สีส้ม ในข้อความเดียว (carousel เลื่อนดูได้ 3 การ์ด)
    ใช้สำหรับรอบแจ้งเตือนประจำวัน (เช่น 08:32 / 09:05 / 17:05) — ส่งครั้งเดียวครบทุกแหล่ง
    """
    bbl_rate = scrape_bbl_jpy()
    sr_rate = scrape_superrich_jpy()
    sr_orange_rate = scrape_superrich_orange_jpy()

    bbl_bubble = _build_rate_bubble(
        label="BBL",
        desc=f"📊 ({_bkk_now()}) -- อัตราแลกเปลี่ยนธนาคารกรุงเทพ",
        rate=bbl_rate,
        link_label="BBL Rate",
        link_url=BBL_URL_DISPLAY,
        header_color=COLOR_BBL_LABEL,
        link_color=COLOR_BBL_LINK,
    )
    sr_bubble = _build_rate_bubble(
        label="SUPER RICH สีเขียว",
        desc=f"📊 ({_bkk_now()}) -- อัตราแลกเปลี่ยนซุปเปอร์ริช สีเขียว",
        rate=sr_rate,
        link_label="SUPER RICH สีเขียว Rate",
        link_url=SR_URL_DISPLAY,
        header_color=COLOR_SR_GREEN,
        link_color=COLOR_SR_GREEN,
    )
    sr_orange_bubble = _build_rate_bubble(
        label="SUPER RICH สีส้ม",
        desc=f"📊 ({_bkk_now()}) -- อัตราแลกเปลี่ยนซุปเปอร์ริช สีส้ม",
        rate=sr_orange_rate,
        link_label="SUPER RICH สีส้ม Rate",
        link_url=SR_ORANGE_URL_DISPLAY,
        header_color=COLOR_SR_ORANGE,
        link_color=COLOR_SR_ORANGE,
    )

    carousel = {"type": "carousel", "contents": [bbl_bubble, sr_bubble, sr_orange_bubble]}
    safe_push_flex(
        f"BBL JPY {bbl_rate} | SR เขียว JPY {sr_rate} | SR ส้ม JPY {sr_orange_rate}",
        carousel,
    )

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
async def test_capture(type: str = None):
    if type == "bbl":
        send_bbl()
    elif type == "superrich":
        send_superrich()
    elif type == "superrich_orange":
        send_superrich_orange()
    elif type == "combined":
        send_combined()
    else:
        return JSONResponse(
            content={"error": "Missing or invalid ?type= parameter. Valid values: bbl, superrich, superrich_orange, combined."},
            status_code=400
        )
    return {"status": "triggered", "type": type}

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
        "TZ": "Asia/Bangkok (+7UTC)"
    }
