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

def get_best_model():
    """自動尋找目前可用的模型"""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if 'models/gemini-1.5-flash' in available_models:
            return genai.GenerativeModel('gemini-1.5-flash')
        elif 'models/gemini-pro' in available_models:
            return genai.GenerativeModel('gemini-pro')
        elif available_models:
            return genai.GenerativeModel(available_models[0].replace('models/', ''))
    except Exception:
        return genai.GenerativeModel('gemini-1.5-flash')

# 【新增】觸發關鍵字清單
TRIGGER_WORDS = ["多少錢", "行情", "實價登錄", "成交價", "房價"]

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Hello, Rainie! Little Raindrop is ready."
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

    # 【新增】檢查是否包含關鍵字，若無則不回覆 (人工回覆模式)
    if not any(word in user_text for word in TRIGGER_WORDS):
        return

    try:
        model = get_best_model()
        prompt = f"你是房仲雨榛的智慧助手小雨滴，請用親切、專業、生活化的口吻回答：{user_text}"
        response = model.generate_content(prompt)

        if response and response.text:
            reply_text = response.text
        else:
            reply_text = "小雨滴正在努力思考中，請再試一次。"

    except Exception as e:
        try:
            model_list = [m.name for m in genai.list_models()]
            reply_text = f"報告雨榛，小雨滴出錯了。\n錯誤：{str(e)}\n可用模型：{', '.join(model_list[:3])}"
        except:
            reply_text = f"報告雨榛，連線失敗：{str(e)}"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
