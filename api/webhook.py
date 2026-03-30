import os
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai

app = Flask(__name__)

# ==========================================
# ✨ 第一區：小雨滴的靈魂設定 (妳可以在這裡隨意交代她)
# ==========================================
LITTLE_RAINDROP_PERSONA = """
你是房仲雨榛的智慧助手「小雨滴」。
妳現在正在跟雨榛的 LINE 客戶聊天，請遵守以下人設：

1. 妳的人格：親切、專業、生活化，像雨榛的好夥伴。

2. 說話原則：精簡、白話、不要長篇大論，盡量擬人化，不要有 AI 感。

3. 觸發時機：當客戶問到錢、行情、實價登錄時，妳才出來專業回覆。

4. 專業任務：請用妳掌握的大數據，提供精準、來源正規的房地產行情。
"""
# ==========================================

# 讀取金鑰
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

def get_best_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if 'models/gemini-1.5-flash' in available_models:
            return genai.GenerativeModel('gemini-1.5-flash', system_instruction=LITTLE_RAINDROP_PERSONA)
        return genai.GenerativeModel('gemini-pro', system_instruction=LITTLE_RAINDROP_PERSONA)
    except:
        return genai.GenerativeModel('gemini-1.5-flash', system_instruction=LITTLE_RAINDROP_PERSONA)

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

    # 只有關鍵字才觸發
    if not any(word in user_text for word in TRIGGER_WORDS):
        return

    try:
        model = get_best_model()
        # 這裡只需要把客戶的問題傳給她，她會記得上面的靈魂設定
        response = model.generate_content(user_text)

        if response and response.text:
            reply_text = response.text
        else:
            reply_text = "小雨滴正在努力思考中，請再試一次。"

    except Exception as e:
        reply_text = f"（連線失敗，我請雨榛親自回覆您喔！）"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    app.run()
