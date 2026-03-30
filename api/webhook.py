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
        return "Little Raindrop 2.0 - Debug Mode"
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

    try:
        # 設定指令：小雨滴專業報表版
        prompt = (
            f"你是房仲雨榛的助手小雨滴。針對問題：『{user_text}』，請執行：\n"
            "1. 搜尋樂居(leju.com.tw)或實價登錄最新資訊。\n"
            "2. 整理出該社區『近一年內』的成交明細，包含：地址、格局、型態、車位、單價、總價、成交日期。\n"
            "3. 語氣親切擬人且簡短（150字內），結尾引導客戶找雨榛細算。"
        )

        # 嘗試使用搜尋功能
        try:
            model = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                tools=[{"google_search_retrieval": {}}]
            )
            response = model.generate_content(prompt)
            reply_text = response.text
        except Exception:
            # 如果搜尋工具失敗，改用標準模式
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            reply_text = f"（搜尋功能暫時休息，由我記憶庫回報）：\n{response.text}"

    except Exception as e:
        # 出錯時直接把錯誤傳回手機，方便 debug
        reply_text = f"報告雨榛，小雨滴在查資料時出錯了：\n{str(e)[:100]}"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
