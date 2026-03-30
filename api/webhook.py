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

# 核心設定：使用具備 Google 搜尋功能的 Gemini 1.5 Flash
# 修正 404 關鍵：必須使用完整路徑 models/gemini-1.5-flash
model = genai.GenerativeModel(
    model_name='models/gemini-1.5-flash',
    tools=[{"google_search_retrieval": {}}]
)

# 觸發關鍵字
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價", "單價", "價格"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Little Raindrop 2.0 - Real-time Search Edition"
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

    # 【深度搜尋指令】要求 7 個專業欄位
    prompt = (
        f"請上網搜尋『樂居 leju.com.tw』或『內政部實價登錄』，查詢關於：『{user_text}』的最新成交資訊。\n\n"
        "【任務要求】\n"
        "你是房仲雨榛的助手小雨滴，請提供該社區『近一年內』的成交明細。\n"
        "資訊必須精準包含以下 7 個欄位：\n"
        "1. 地址(棟別)\n"
        "2. 格局\n"
        "3. 型態\n"
        "4. 車位有無\n"
        "5. 單價(萬/坪)\n"
        "6. 總價(萬元)\n"
        "7. 成交日期\n\n"
        "【回覆原則】\n"
        "- 語氣親切、專業、生活化，不要長篇大論。\n"
        "- 請用『📍』作為每筆成交的開頭。\n"
        "- 結尾引導客戶：『數據只是參考，建議讓雨榛幫您現場看屋估算更準喔！』"
    )

    try:
        # 執行具備聯網能力的搜尋與回覆
        response = model.generate_content(prompt)

        if response and response.text:
            reply_text = response.text
        else:
            reply_text = "哎呀，這區的資料小雨滴正在努力抓取中，稍等我一下喔！"

    except Exception as e:
        # 如果聯網搜尋失敗，嘗試降級回標準回覆，避免讓客戶看到 404
        try:
            standard_model = genai.GenerativeModel('models/gemini-1.5-flash')
            res = standard_model.generate_content(f"請簡短介紹一下這間社區的行情：{user_text}")
            reply_text = f"（搜尋暫時繁忙，小雨滴先回報大數據行情）：\n{res.text}"
        except:
            reply_text = f"報告雨榛，連線大腦出錯了：{str(e)[:50]}"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
