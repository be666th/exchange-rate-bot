import schedule
import time
import datetime
import requests
import os
import holidays
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

load_dotenv()
LINE_NOTIFY_TOKEN = os.getenv('LINE_NOTIFY_TOKEN')

def send_line_notify(message, image_path):
    url = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {LINE_NOTIFY_TOKEN}'}
    data = {'message': message}
    files = {'imageFile': open(image_path, 'rb')}
    requests.post(url, headers=headers, data=data, files=files)

def is_working_day():
    today = datetime.date.today()
    return today.weekday() < 5 and today not in holidays.Thailand()

def capture_screenshot(url, filename):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1280,800')
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(5)
    driver.save_screenshot(filename)
    driver.quit()

def job():
    if not is_working_day():
        print("วันนี้วันหยุด ไม่ทำงาน")
        return

    urls = {
        "BBL": "https://www.bangkokbank.com/th-TH/Personal/Other-Services/Rates-Fees/Foreign-Exchange-Rates",
        "BOT": "https://www.bot.or.th/th/statistics/exchange-rate.html"
    }

    for name, url in urls.items():
        filename = f"{name}.png"
        capture_screenshot(url, filename)
        send_line_notify(f"{name} - Baht to JPY", filename)

schedule.every().day.at("08:31").do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
