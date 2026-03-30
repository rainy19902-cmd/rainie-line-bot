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

# 修正：使用 gemini-1.5-flash，這是目前免費版最穩定且功能最強的模型
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route("/api/webhook", methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        return "Hello, Rainie! Little Raindrop is ready!"

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
        # 設定角色指令
        prompt = f"你是房仲雨榛的智慧助手小雨滴，請用親切、專業、生活化的口吻回答客戶：{user_text}"

        # 呼叫 Gemini
        response = model.generate_content(prompt)

        # 檢查回覆
        if response and response.text:
            reply_text = response.text
        else:
            reply_text = "小雨滴正在努力思考中，請稍後再試一次。"

    except Exception as e:
        # 如果出錯，回報錯誤原因
        reply_text = f"報告雨榛，小雨滴遇到問題了：{str(e)}"

    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
