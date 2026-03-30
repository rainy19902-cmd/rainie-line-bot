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

# 核心設定：使用穩定版 Gemini 1.5 Flash
model = genai.GenerativeModel('gemini-1.5-flash')

# 觸發關鍵字
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "單價", "價格"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop 3.0 - Diagnosis Mode"
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

    # 專業報表指令
    prompt = (
        f"你是房仲雨榛的助手小雨滴。針對：『{user_text}』，請根據你的資料庫列出該社區近一年成交明細。\n"
        "必須包含：地址、格局、型態、車位、單價、總價、成交日期。語氣親切，結尾引導找雨榛。"
    )

    try:
        # 呼叫 Gemini
        response = model.generate_content(prompt)

        if response and response.text:
            reply_text = response.text
        else:
            reply_text = "報告雨榛，小雨滴的大腦沒給出任何回應..."

    except Exception as e:
        # 【診斷核心】直接把錯誤原因回傳到手機
        error_msg = str(e)
        reply_text = f"報告雨榛，小雨滴連線大腦失敗了！\n原因：{error_msg[:150]}"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
