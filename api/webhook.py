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

# 核心設定：使用穩定版 Gemini 1.5 Flash (不加 tools 以避免 404 報錯)
model = genai.GenerativeModel('gemini-1.5-flash')

# 觸發關鍵字
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "單價", "價格"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop 3.0 - Professional Report Mode"
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

    # 【深度數據報表指令】強制要求 7 個欄位
    prompt = (
        f"你是房仲雨榛的專業助手小雨滴。針對社區：『{user_text}』，請根據你掌握的實價登錄大數據，回報該社區近一年的成交狀況。\n\n"
        "【任務要求】\n"
        "1. 請列出至少 3 筆該社區近一年的成交明細。\n"
        "2. 每筆成交必須包含：地址(棟別)、格局、型態、車位有無、單價(萬/坪)、總價(萬元)、成交日期。\n"
        "3. 語氣要親切、像真人，請用『📍』作為清單開頭。\n"
        "4. 最後請附上樂居網的搜尋連結：https://www.leju.com.tw/search_home?q={user_text}\n"
        "5. 結尾請引導客戶找雨榛細算。例如：『數據只是參考，建議讓雨榛幫您現場看屋估算更準喔！』"
    )

    try:
        # 呼叫 Gemini 產生報表
        response = model.generate_content(prompt)

        if response and response.text:
            reply_text = response.text
        else:
            search_url = f"https://www.leju.com.tw/search_home?q={user_text}"
            reply_text = f"哈囉！這區的行情我正在幫您整理中，您可以先看這邊的最新數據：\n{search_url}\n我馬上請雨榛親自回您喔！"

    except Exception as e:
        search_url = f"https://www.leju.com.tw/search_home?q={user_text}"
        reply_text = f"哈囉！現在小雨滴連線有點忙，您可以先點這裡看行情：\n{search_url}\n我請雨榛等等回您！"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
