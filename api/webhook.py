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

# 2. 設定最穩定的模型 (不加工具，確保 100% 通話)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. 觸發關鍵字
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "價格", "單價"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop 3.0 - Stable and Simple Edition"
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

    # 檢查關鍵字，沒觸發就沈默 (這就是妳要的人工模式)
    should_trigger = any(word in user_text for word in TRIGGER_WORDS)
    if not should_trigger:
        return 

    # 4. 極致簡約的報表指令
    prompt = (
        f"你是房仲雨榛的助手小雨滴。請針對社區『{user_text}』回答以下資訊：\n\n"
        "1. 該社區近一年的成交平均單價與總價範圍。\n"
        "2. 列出至少 2-3 筆近一年的成交明細，格式必須包含：\n"
        "   地址(棟別)、格局、型態、車位、單價(萬/坪)、總價(萬)、成交日期。\n"
        "3. 語氣親切有禮，150 字以內，結尾要引導客戶找雨榛細算。\n"
        f"4. 附上樂居搜尋連結：https://www.leju.com.tw/search_home?q={user_text}"
    )

    try:
        # 呼叫 Gemini 產生資料
        response = model.generate_content(prompt)
        reply_text = response.text if response.text else "抱歉，這區資料我正在整理，請雨榛幫您看看喔！"

    except Exception:
        # 萬一出錯，直接給連結，這最保險
        search_url = f"https://www.leju.com.tw/search_home?q={user_text}"
        reply_text = f"哈囉！這間社區的最新行情您可以點這裡看喔：\n{search_url}\n詳細細節我請雨榛等等回覆您！"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
