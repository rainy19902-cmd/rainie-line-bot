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

# 2. 自動偵測可用模型 (解決 404 報錯)
def get_working_model():
    try:
        # 抓取這把 Key 權限下所有可用的模型
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # 優先順序：1.5-flash > gemini-pro
                if 'gemini-1.5-flash' in m.name:
                    return genai.GenerativeModel(m.name)
        # 如果沒找到 1.5，就回傳一個保底模型
        return genai.GenerativeModel('gemini-pro')
    except:
        # 如果連列清單都失敗，直接強制使用最通用的名稱
        return genai.GenerativeModel('models/gemini-1.5-flash')

# 3. 觸發關鍵字
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "單價", "價格"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop 3.0 - Auto Diagnosis Active"
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

    # 【專業報表指令】鎖定 7 個欄位
    prompt = (
        f"你是房仲雨榛的專業助手小雨滴。針對問題：『{user_text}』，請根據你掌握的實價登錄數據進行回答。\n\n"
        "【任務要求】\n"
        "1. 請列出該社區『近一年內』的成交明細。\n"
        "2. 每筆成交必須嚴格包含：地址(棟別)、格局、型態、車位有無、單價(萬/坪)、總價(萬元)、成交日期。\n"
        "3. 語氣親切擬人，請用『📍』作為每筆成交開頭。\n"
        "4. 結尾請引導客戶找雨榛細算，例如：『數據只是參考，建議讓雨榛幫您現場看屋估算更準喔！』"
    )

    try:
        # 呼叫自動偵測的模型
        model = get_working_model()
        response = model.generate_content(prompt)

        if response and response.text:
            reply_text = response.text
        else:
            reply_text = f"哈囉！小雨滴正在努力翻閱實價登錄，請再給我一次機會測試！"

    except Exception as e:
        # 如果還是失敗，把最後的底牌報出來
        reply_text = f"報告雨榛，小雨滴連線失敗：{str(e)[:50]}"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
