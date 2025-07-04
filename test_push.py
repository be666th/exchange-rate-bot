from linebot import LineBotApi
from linebot.models import TextSendMessage
import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
group_id = os.getenv("GROUP_ID")

line_bot_api = LineBotApi(token)
line_bot_api.push_message(group_id, TextSendMessage(text="✅ Test push from VPS success+++GCG1++สวัสดีจ้าาาาา++"))
print("✅ Push sent")
