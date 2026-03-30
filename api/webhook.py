import os
import json
import re
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
model = genai.GenerativeModel('gemini-1.5-flash')

# 觸發關鍵字清單
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "價格", "單價", "明細"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop 2.0 is helping Rainie!"
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

    # 檢查是否觸發關鍵字
    should_trigger = any(word in user_text for word in TRIGGER_WORDS)
    if not should_trigger:
        return 

    # 1. 精準提取社區名稱 (過濾掉所有雜質字)
    clean_name = user_text
    for word in TRIGGER_WORDS:
        clean_name = clean_name.replace(word, "")
    # 過濾問號、空格、以及「幫我找、查」等動詞
    clean_name = re.sub(r'[？?！!，。：\s]|幫我找|幫我查|我想看|查|看', '', clean_name).strip()

    # 2. 專業明細指令
    prompt = (
        f"你是房仲雨榛的專業助理小雨滴。客戶詢問：『{user_text}』，請執行：\n\n"
        f"1. 針對『{clean_name}』社區，先用親切的口吻打招呼並簡析周邊環境。\n"
        "2. 列出該社區近一年內成交明細(2-3筆)。格式如下：\n"
        "   📍地址(棟別)：\n"
        "   格局/型態：\n"
        "   車位有無：\n"
        "   單價/總價：\n"
        "   成交日期：\n"
        "3. 最後說明數據僅供參考，引導找雨榛細算。\n"
        f"4. 附上精準連結：https://www.leju.com.tw/community_list?search_name={clean_name}"
    )

    try:
        response = model.generate_content(prompt)
        if response and response.text:
            reply_text = response.text
        else:
            raise ValueError("Empty Response")

    except Exception as e:
        # 備援回覆：確保樂居網址也是乾淨的
        search_url = f"https://www.leju.com.tw/community_list?search_name={clean_name}"
        reply_text = f"哈囉！小雨滴現在查資料有點擠，您可以先點這裡看最新行情：\n{search_url}\n詳細細節我請雨榛等等回覆您！"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
