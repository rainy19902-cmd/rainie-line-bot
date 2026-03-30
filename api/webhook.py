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

# 2. 設定穩定版模型 (不加搜尋工具，確保 100% 正常回話)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. 觸發關鍵字
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "價格", "單價"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop 3.0 - Text Report Mode"
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

    # 原則 1：關鍵字偵測
    should_trigger = any(word in user_text for word in TRIGGER_WORDS)
    if not should_trigger:
        return 

    # 4. 提取社區名稱 (過濾關鍵字，避免搜尋連結出錯)
    clean_name = user_text
    for word in TRIGGER_WORDS:
        clean_name = clean_name.replace(word, "")
    clean_name = clean_name.replace("?", "").replace("？", "").strip()

    # 5. 強化文字報表指令 (像對話一樣呈現)
    prompt = (
        f"你是房仲雨榛的智慧助手小雨滴。針對客戶詢問：『{user_text}』，請根據你的專業數據回報明細。\n\n"
        "回答原則：\n"
        "1. 語氣要像真人聊天、親切簡短。先給一個溫馨的開頭。\n"
        "2. 請直接用文字列出該社區近一年的成交狀況，必須包含這 7 個欄位：\n"
        "   📍地址(棟別)、格局、型態、車位有無、單價、總價、成交日期。\n"
        "3. 不要用死板的表格，請用『📍』作為每筆明細的開頭。\n"
        "4. 回答最後附上樂居搜尋連結：https://www.leju.com.tw/community_list?search_name={clean_name}\n"
        "5. 最後要引導客戶找雨榛細算。例如：『這是我幫您查到的數據，細節我請雨榛幫您評估好嗎？』\n\n"
        "請開始親切的回報："
    )

    try:
        # 呼叫大腦產生對話
        response = model.generate_content(prompt)
        reply_text = response.text if response.text else "哎呀，這區資料我正在整理中，我請雨榛等等回您喔！"

    except Exception:
        # 保底機制：萬一 AI 斷線，直接給正確的搜尋網址
        search_url = f"https://www.leju.com.tw/community_list?search_name={clean_name}"
        reply_text = f"哈囉！這間社區的最新行情您可以點這裡看喔：\n{search_url}\n詳細細節我請雨榛等等親自回覆您！"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
