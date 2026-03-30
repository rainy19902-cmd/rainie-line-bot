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
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. 觸發關鍵字 (人工回覆原則)
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "單價", "價格"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop is ready to help!"
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

    # 檢查關鍵字，沒觸發就保持沈默讓人工回覆
    should_trigger = any(word in user_text for word in TRIGGER_WORDS)
    if not should_trigger:
        return 

    # 3. 提取純社區名稱
    clean_name = user_text
    for word in TRIGGER_WORDS:
        clean_name = clean_name.replace(word, "")
    clean_name = re.sub(r'[？?！!，。：\s]|幫我找|幫我查|我想看|查|看', '', clean_name).strip()

    # 4. 仿造截圖格式的專業指令
    prompt = (
        f"你是房仲雨榛的專業助理小雨滴。針對客戶詢問『{user_text}』，請參考最新實價登錄數據，嚴格依照以下格式回覆：\n\n"
        f"幫你整理了『{clean_name}』社區的近一年實價登錄現況、周邊建設環境評分，以及未來的漲幅預測：\n\n"
        "💰 近一年實價登錄 (2023~2024 / 2025初)\n\n"
        "．平均單價：約 [請填寫數據] 萬 ～ [請填寫數據] 萬 / 坪\n"
        "．屋齡：約 [請填寫數據] 年 (總戶數 [數字] 戶)\n"
        "．產品規劃：[坪數範圍] 坪\n"
        "．公設比：約 [數字]%\n"
        "(註：[請提供一段關於該社區行情水平、未來漲幅可能性的專業白話分析])\n\n"
        "---\n"
        "數據僅供參考，細節我請雨榛幫您評估好嗎？\n\n"
        f"🔗 樂居連結：https://www.leju.com.tw/community_list?search_name={clean_name}"
    )

    try:
        response = model.generate_content(prompt)
        if response and response.text:
            reply_text = response.text
        else:
            raise ValueError("Empty Response")

    except Exception:
        search_url = f"https://www.leju.com.tw/community_list?search_name={clean_name}"
        reply_text = (
            f"幫您查詢『{clean_name}』的行情如下：\n"
            f"目前資料更新中，您可以先參考樂居的即時數據喔：\n{search_url}\n"
            "我也會請雨榛等等親自回覆您細節！"
        )

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
