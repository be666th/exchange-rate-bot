from dotenv import load_dotenv
load_dotenv()

import os
from linebot import LineBotApi
from linebot.models import TextSendMessage

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
line_bot_api.push_message(
    GROUP_ID,
    TextSendMessage(text="✅ Test message from bot (minimal test)")
)
print("✅ Push message sent.")
