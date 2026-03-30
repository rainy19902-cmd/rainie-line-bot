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

# 啟用 Google 搜尋工具 (這會讓小雨滴去查樂居、實價登錄)
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    tools=[{"google_search_retrieval": {}}]
)

# 觸發小雨滴的關鍵字 (只要有提到這些，小雨滴才會出動)
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop 2.0 - Ready to assist Rainie!"
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

    # 原則 1：檢查是否包含關鍵字，沒有的話就保持沈默 (人工回覆模式)
    should_trigger = any(word in user_text for word in TRIGGER_WORDS)
    if not should_trigger:
        return 

    try:
        # 原則 2, 3, 5：小雨滴的個性設定
        prompt = (
            f"你是智慧助手小雨滴。請針對使用者的問題：『{user_text}』進行回答。\n\n"
            "規則如下：\n"
            "1. 必須親自上網查詢『樂居 (leju.com.tw)』或『內政部實價登錄』獲取最新精準資訊。\n"
            "2. 說話要像真人、親切有禮貌且簡短，不要長篇大論，回答控制在 100 字以內。\n"
            "3. 用白話文直接講單價範圍或總價趨勢，不要用 AI 的列點格式。\n"
            "4. 結尾要引導客戶找雨榛處理細節。例如：『這區行情大概是這樣，要不要我請雨榛幫妳細算一下？』\n"
            "5. 如果查不到，就說：『哎呀這社區太神祕了，我幫妳標記一下，讓雨榛等下親自回妳喔！』"
        )

        response = model.generate_content(prompt)
        reply_text = response.text if response.text else "我請雨榛等等親自回妳喔！"

    except Exception:
        # 發生錯誤時保持沈默，讓人工作業，避免客人看到錯誤碼
        return

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
