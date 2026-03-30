import os
import json
import re
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
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if 'models/gemini-1.5-flash' in available_models:
            return genai.GenerativeModel('gemini-1.5-flash')
        return genai.GenerativeModel('gemini-pro')
    except:
        return genai.GenerativeModel('gemini-1.5-flash')

# 2. 觸發關鍵字
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "價格", "單價"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop 2.0 is active."
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

    # 檢查關鍵字，若無則沈默
    if not any(word in user_text for word in TRIGGER_WORDS):
        return

    # 3. 提取社區名稱
    clean_name = user_text
    for word in TRIGGER_WORDS:
        clean_name = clean_name.replace(word, "")
    clean_name = re.sub(r'[？?！!，。：\s]|幫我找|幫我查|我想看|查|看', '', clean_name).strip()

    # 4. 強制縮短回覆並鎖定格式 (仿照截圖)
    prompt = (
        f"你是房仲雨榛的專業助理小雨滴。針對客戶詢問『{user_text}』，請根據你的數據庫，『嚴格禁止長篇大論』，僅准依照以下格式回覆：\n\n"
        f"幫你整理了『{clean_name}』社區的近一年實價登錄現況、周邊建設環境評分，以及未來的漲幅預測：\n\n"
        "💰 近一年實價登錄 (2023~2024 / 2025初)\n\n"
        "．平均單價：約 [請填入] 萬 ～ [請填入] 萬 / 坪\n"
        "．屋齡：約 [請填入] 年\n"
        "．產品規劃：[請填入] 坪\n"
        "．公設比：約 [數字]%\n"
        "(註：[請用30字內分析該社區行情水平及漲幅潛力])\n\n"
        "---\n"
        "數據僅供參考，細節我請雨榛幫您評估好嗎？"
    )

    try:
        model = get_best_model()
        response = model.generate_content(prompt)
        reply_text = response.text if response.text else "小雨滴正在整理資料，請稍候。"
    except Exception:
        reply_text = f"幫您查詢『{clean_name}』的行情資料更新中，我請雨榛等等親自回覆您！"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
