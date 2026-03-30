import os
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai

app = Flask(__name__)

# 設定金鑰
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-pro')

# 只要敲 /api/webhook 這個門，不論 GET 還是 POST 都會回應
@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Hello, Rainie! Your Webhook is alive!"

    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        json_body = json.loads(body)
        if not json_body.get('events'):
            return 'OK'
    except:
        pass

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    try:
        prompt = f"你是房仲雨榛的智慧助手小雨滴，請用親切、專業、生活化的口吻回答：{user_text}"
        response = model.generate_content(prompt)
        reply_text = response.text if response.text else "小雨滴正在思考中，請稍後..."
    except Exception as e:
        reply_text = f"報告雨榛，小雨滴遇到一點問題：{str(e)}"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    app.run()
