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

# 觸發關鍵字
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "單價", "價格"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop 2.0 - Final Shield Active"
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

    # 檢查關鍵字，沒觸發就沈默 (人工回覆模式)
    should_trigger = any(word in user_text for word in TRIGGER_WORDS)
    if not should_trigger:
        return 

    # 【深度搜尋指令】
    prompt = (
        f"你是房仲雨榛的助手小雨滴。請針對社區『{user_text}』，整理出『近一年內』的成交明細。\n\n"
        "必須包含：1.地址(棟別) 2.格局 3.型態 4.車位 5.單價 6.總價 7.成交日期。\n"
        "語氣要親切口語，控制在 150 字內，結尾引導客戶找雨榛細算。"
    )

    try:
        try:
            # 【策略 A】嘗試最新聯網語法
            model = genai.GenerativeModel('gemini-1.5-flash', tools='google_search')
            response = model.generate_content(prompt)
            reply_text = response.text
        except Exception:
            # 【策略 B】如果聯網報 404，改用標準智慧回覆，並附上樂居搜尋連結
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            search_url = f"https://www.leju.com.tw/search_home?q={user_text}"
            reply_text = f"{response.text}\n\n💡 這邊有最新的樂居實登連結可以參考：\n{search_url}"

    except Exception as e:
        # 如果連 AI 都出錯，至少提供樂居連結給客戶，保住妳的專業形象
        search_url = f"https://www.leju.com.tw/search_home?q={user_text}"
        reply_text = f"哈囉！小雨滴現在查資料有點擠，您可以先點這裡看最新行情：\n{search_url}\n我馬上請雨榛親自回您喔！"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
