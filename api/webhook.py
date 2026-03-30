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

# 2. 觸發關鍵字
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "單價", "價格", "多少"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop is ready!"
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

    # 3. 超強名稱過濾器 (確保樂居網址 100% 正確)
    clean_name = user_text
    # 移除所有關鍵字
    for word in TRIGGER_WORDS + ["幫我查", "幫我找", "我想看", "查詢", "社區", "的"]:
        clean_name = clean_name.replace(word, "")
    # 移除符號與空格
    clean_name = re.sub(r'[？?！!，。：\s]', '', clean_name).strip()

    # 4. 仿造截圖格式的專業指令 (精簡化以防出錯)
    prompt = (
        f"你是房仲雨榛的專業助理小雨滴。針對客戶詢問『{user_text}』，請根據你的房地產數據庫，嚴格依照以下格式回覆（不要給明細，只要摘要）：\n\n"
        f"幫你整理了『{clean_name}』社區的近一年實價登錄現況、周邊建設環境評分，以及未來的漲幅預測：\n\n"
        "💰 近一年實價登錄 (2023~2024 / 2025初)\n\n"
        "．平均單價：約 [數據] 萬 ～ [數據] 萬 / 坪\n"
        "．屋齡：約 [數據] 年\n"
        "．產品規劃：[坪數] 坪\n"
        "．公設比：約 [數字]%\n"
        "(註：[提供一段專業的行情水平與未來潛力分析])\n\n"
        "---\n"
        "數據僅供參考，細節我請雨榛幫您評估好嗎？\n\n"
        f"🔗 樂居連結：https://www.leju.com.tw/community_list?search_name={clean_name}"
    )

    try:
        # 呼叫 Gemini
        response = model.generate_content(prompt)
        if response and response.text:
            reply_text = response.text
        else:
            raise ValueError("Empty")

    except Exception:
        # 萬一 AI 失敗，提供正確的連結
        search_url = f"https://www.leju.com.tw/community_list?search_name={clean_name}"
        reply_text = (
            f"幫您查詢『{clean_name}』的行情如下：\n"
            f"目前小雨滴大腦連線較慢，您可以先參考樂居的即時數據喔：\n{search_url}\n"
            "我也會請雨榛等等親自回覆您細節！"
        )

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
