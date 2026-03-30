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
        return "Little Raindrop 2.0 - Real Estate Professional Edition"
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

    # 【核心指令】設定小雨滴的專業報表邏輯
    prompt = (
        f"你是房仲雨榛的助手小雨滴。請針對：『{user_text}』進行回答。\n\n"
        "【專業任務】\n"
        "1. 請優先上網查詢樂居(leju.com.tw)或實價登錄，整理出該社區『近一年內』的成交明細。\n"
        "2. 資訊必須包含：地址(棟別)、格局、型態、車位有無、單價、總價、成交日期。\n"
        "3. 請用親切、口語化的方式開頭，並將明細整理得清晰易讀（每筆成交一組，不要堆疊）。\n"
        "4. 回答要準確、精簡，最後引導客戶找雨榛進行深度環境分析或細算。\n\n"
        "【回覆範例參考】\n"
        "『哈囉！幫妳查了一下有富藏玉近一年的實登狀況，這幾筆給妳參考：\n"
        "📍 10樓(C棟) / 3房 / 大樓 / 平車 / 單價XX萬 / 總價XXXX萬 (113/05)\n"
        "📍 8樓(B棟) / 2房 / 大樓 / 無車位 / 單價XX萬 / 總價XXXX萬 (112/12)\n\n"
        "價格會隨樓層裝潢有差，要不要我請雨榛幫妳細算一下？』"
    )

    try:
        # 優先嘗試聯網搜尋
        try:
            model_with_search = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                tools=[{"google_search_retrieval": {}}]
            )
            response = model_with_search.generate_content(prompt)
            reply_text = response.text
        except:
            # 備援：如果搜尋工具出錯，使用標準模型回答
            standard_model = genai.GenerativeModel('gemini-1.5-flash')
            response = standard_model.generate_content(prompt)
            reply_text = response.text

    except Exception as e:
        # 極致防錯：如果連 AI 都沒回應，保持沈默讓人工作業
        return

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
