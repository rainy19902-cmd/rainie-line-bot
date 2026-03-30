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
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. 觸發關鍵字
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "價格", "單價"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop is assisting Rainie!"
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

    # 關鍵字過濾
    should_trigger = any(word in user_text for word in TRIGGER_WORDS)
    if not should_trigger:
        return 

    # 提取社區名稱
    clean_name = user_text
    for word in TRIGGER_WORDS:
        clean_name = clean_name.replace(word, "")
    clean_name = clean_name.replace("?", "").replace("？", "").replace("幫我找", "").strip()

    # 3. 強化指令：要求提供 7 個欄位的成交明細
    prompt = (
        f"你是房仲雨榛的智慧助手小雨滴。客戶詢問：『{user_text}』，請執行以下任務：\n\n"
        "1. 先用親切、擬人的語氣開頭，簡單分析該社區環境與未來潛力。\n"
        "2. 【重要】請根據你的實價登錄大數據，列出該社區『近一年內』的成交明細（至少 3 筆）。\n"
        "3. 每筆明細必須包含：📍地址(棟別)、格局、型態、車位有無、單價、總價、成交日期。\n"
        "4. 結尾引導客戶：『數據只是參考，建議讓雨榛幫您現場看屋估算更準喔！』\n"
        f"5. 最後附上正確的樂居連結：https://www.leju.com.tw/community_list?search_name={clean_name}\n\n"
        "請開始親切的回報："
    )

    try:
        response = model.generate_content(prompt)
        reply_text = response.text if response.text else "這區資料我正在整理中，我請雨榛等等親自回您喔！"

    except Exception:
        search_url = f"https://www.leju.com.tw/community_list?search_name={clean_name}"
        reply_text = f"哈囉！這間社區的最新行情您可以先點這裡看喔：\n{search_url}\n詳細細節我請雨榛等等回覆您！"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
