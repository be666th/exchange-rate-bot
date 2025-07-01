from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage

import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    print("Request body: " + body)  # ✅ print event JSON เพื่อตรวจสอบ group_id

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("✅ Group ID:", event.source.group_id)  # ✅ print group_id ที่นี่
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="✅ Bot received your message")
    )

if __name__ == "__main__":
    app.run()
