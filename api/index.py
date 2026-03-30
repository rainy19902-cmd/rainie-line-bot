import os
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai

# 1. 初始化 Flask 伺服器
app = Flask(__name__)

# 2. 從 Vercel 環境變數讀取金鑰 (請確認 Vercel 後台的名字一模一樣)
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# 3. 設定 Gemini 1.5 Flash 模型
model = genai.GenerativeModel('gemini-1.5-flash')

# 4. 根目錄測試路由 (點擊網址會看到這行字)
@app.route("/", methods=['GET'])
def hello():
    return "Hello, Rainie! Your AI Bot 'Little Raindrop' is running perfectly!"

# 5. LINE Webhook 進入點
@app.route("/api/webhook", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    # 處理 LINE Developers 的 Verify 按鈕 (空事件處理)
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

# 6. 處理使用者傳來的文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text

    try:
        # 設定 AI 的角色扮演指令：小雨滴版 💧
        prompt = f"你是房仲雨榛的智慧助手小雨滴，請用親切、專業、生活化的口吻回答使用者的問題：{user_text}"

        # 呼叫 Gemini API 產生回覆
        response = model.generate_content(prompt)

        # 檢查是否有產生文字
        if response.text:
            reply_text = response.text
        else:
            reply_text = "報告雨榛，小雨滴這次沒有給出回應，可能是內容被過濾了。"

    except Exception as e:
        # 如果出錯，會直接傳回具體的錯誤原因，方便我們抓蟲
        reply_text = f"報告雨榛，小雨滴連線到大腦時出錯了：\n{str(e)}"

    # 將結果回傳給使用者的 LINE
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
