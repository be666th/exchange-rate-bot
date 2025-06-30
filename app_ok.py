from dotenv import load_dotenv
load_dotenv()

import os
import time
import schedule
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from linebot import LineBotApi
from linebot.models import TextSendMessage

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
GROUP_ID = os.getenv("GROUP_ID")

print("LINE_CHANNEL_ACCESS_TOKEN =", LINE_CHANNEL_ACCESS_TOKEN)
print("GROUP_ID =", GROUP_ID)


line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
print("✅ LineBotApi initialized successfully")
line_bot_api.push_message(
    GROUP_ID,
    TextSendMessage(text="✅ Bot ทดสอบส่งข้อความสำเร็จ")
)
print("✅ Push message sent.")



def capture_and_send():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)

    # Capture BOT
    url_bot = "https://www.bot.or.th/th/statistics/exchange-rate.html"
    driver.get(url_bot)
    driver.implicitly_wait(5)
    bot_img = "/tmp/bot.png"
    driver.save_screenshot(bot_img)

    # Capture BBL
    url_bbl = "https://www.bangkokbank.com/th-th/personal/other-services/view-rates/foreign-exchange-rates"
    driver.get(url_bbl)
    driver.implicitly_wait(5)
    bbl_img = "/tmp/bbl.png"
    driver.save_screenshot(bbl_img)

    driver.quit()

    line_bot_api.push_message(
        GROUP_ID,
        TextSendMessage(text="✅ Capture เสร็จแล้ว แต่ต้อง upload image เป็น public URL ก่อนถึงจะส่งภาพได้")
    )

schedule.every().day.at("08:31").do(capture_and_send)

while True:
    schedule.run_pending()
    time.sleep(30)
if __name__ == "__main__":
    capture_and_send()
if __name__ == "__main__":
    capture_and_send()  # หรือ push_message test function


