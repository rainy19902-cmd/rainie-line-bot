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

# 嘗試初始化模型 (增加相容性寫法)
try:
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        tools=[{"google_search_retrieval": {}}]
    )
except:
    model = genai.GenerativeModel('gemini-1.5-flash')

# 觸發關鍵字
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "單價", "價格"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop 2.0 - Debug Mode"
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

    # 檢查關鍵字
    should_trigger = any(word in user_text for word in TRIGGER_WORDS)
    if not should_trigger:
        return 

    try:
        prompt = (
            f"你是房仲雨榛的助手小雨滴。請針對：『{user_text}』進行回答。\n\n"
            "規則：\n"
            "1. 上網查詢樂居或實價登錄獲取最新資訊。\n"
            "2. 語氣親切簡短，控制在 100 字內。\n"
            "3. 結尾引導客戶找雨榛細算。"
        )

        response = model.generate_content(prompt)

        if response and response.text:
            reply_text = response.text
        else:
            reply_text = "小雨滴查到了資料但不知道怎麼說，請雨榛幫妳看看喔！"

    except Exception as e:
        # 【重要】這次出錯會直接回傳錯誤訊息，讓我們知道為什麼不回話
        reply_text = f"報告雨榛，小雨滴在查行情時卡住了：\n{str(e)}"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
