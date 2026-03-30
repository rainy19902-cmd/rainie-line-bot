import os
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai

app = Flask(__name__)

# 1. 讀取金鑰
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

def get_best_model():
    """自動尋找目前可用的模型 (避開 404 報錯)"""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if 'models/gemini-1.5-flash' in available_models:
            return genai.GenerativeModel('gemini-1.5-flash')
        elif 'models/gemini-pro' in available_models:
            return genai.GenerativeModel('gemini-pro')
        return genai.GenerativeModel('gemini-1.5-flash')
    except:
        return genai.GenerativeModel('gemini-1.5-flash')

# 2. 觸發關鍵字
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "價格", "單價"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop 2.0 - Simple & Professional"
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

    # 檢查是否包含關鍵字，若無則保持沈默讓人工回覆
    if not any(word in user_text for word in TRIGGER_WORDS):
        return

    try:
        model = get_best_model()

        # 3. 強制要求 AI 依照截圖格式回覆
        prompt = (
            f"你是房仲雨榛的專業助理小雨滴。針對客戶詢問：『{user_text}』，請根據你的數據庫，嚴格依照以下格式回覆：\n\n"
            "幫你整理了該社區的近一年實價登錄現況、周邊建設環境評分，以及未來的漲幅預測：\n\n"
            "💰 近一年實價登錄 (2023~2024 / 2025初)\n\n"
            "．平均單價：約 [請填寫] 萬 ～ [請填寫] 萬 / 坪\n"
            "．屋齡：約 [請填寫] 年\n"
            "．產品規劃：[請填寫] 坪\n"
            "．公設比：約 [請填寫]%\n"
            "(註：[請提供一段關於該社區行情水平、漲幅可能性的專業白話分析])\n\n"
            "---\n"
            "數據僅供參考，細節我請雨榛幫您評估好嗎？"
        )

        response = model.generate_content(prompt)
        reply_text = response.text if response.text else "小雨滴正在整理資料中，我請雨榛等等親自回您喔！"

    except Exception as e:
        # 出錯時回報錯誤方便 debug
        reply_text = f"報告雨榛，小雨滴連線失敗：{str(e)[:50]}"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
