import os
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai

app = Flask(__name__)

# 讀取金鑰
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# ==========================================
# ✨ 妳交代小雨滴的話 (就像電話裡告知人設一樣，妳可以在這裡隨意修改)
# ==========================================
MY_INSTRUCTIONS = """
你是房仲雨榛的智慧助手「小雨滴」。
請遵守雨榛對妳的要求：

1. 說話親切、專業、生活化，像真人在談天。

2. 簡短精確，不要長篇大論。

3. 妳的任務是提供精準的房地產行情。
"""
# ==========================================

# 觸發關鍵字
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "價格", "單價"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET': return "OK"
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text

    # 只有提到行情相關字眼才回覆
    if not any(word in user_text for word in TRIGGER_WORDS):
        return

    try:
        # 使用最穩定的 1.0 模型
        model = genai.GenerativeModel('gemini-pro')

        # 把妳的交代加上客戶的問題，一起傳給 AI
        full_prompt = f"{MY_INSTRUCTIONS}\n\n現在客戶問妳：『{user_text}』，請依照人設回覆。"

        response = model.generate_content(full_prompt)
        reply_text = response.text if response.text else "小雨滴正在努力思考中，請再試一次。"

    except Exception:
        # 如果真的出錯，讓妳知道
        reply_text = "（小雨滴連線大腦失敗，請雨榛親自回覆您喔！）"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
