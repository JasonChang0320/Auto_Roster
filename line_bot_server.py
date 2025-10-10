from flask import Flask, request, abort
import os
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    ImageMessage,
    TextSendMessage,
)

# ====== 你的原有模組 ======
from ocr.ocr_utils import image_to_text
from ocr.process_text import text_to_calender_event_dict
from auto_calendar.calendar_utils import create_events_in_calendar
from linebot_config import CHANNEL_ACCESS_TOKEN, CHANNEL_SECRET
# ====== 設定 ======
app = Flask(__name__)

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ====== Webhook 路由 ======
@app.route("/callback", methods=["POST"])
def callback():
    # 取得 LINE 傳來的簽章與 body
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK", 200


# ====== 處理圖片訊息 ======
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    user_id = event.source.user_id
    message_id = event.message.id

    try:
        # 下載圖片
        message_content = line_bot_api.get_message_content(message_id)
        file_path = os.path.join(UPLOAD_FOLDER, f"{message_id}.jpg")
        with open(file_path, "wb") as f:
            for chunk in message_content.iter_content():
                f.write(chunk)

        # 呼叫你的 OCR 處理流程
        texts = image_to_text(file_path)
        year, month, new_event_dict = text_to_calender_event_dict(texts)
        create_events_in_calendar(year, month, new_event_dict)

        # 回覆成功訊息
        reply_text = (
            "✅ 已成功解析圖片並建立行事曆事件！\n"
            f"偵測文字：\n{texts[:100]}..."  # 避免太長
        )
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

    except Exception as e:
        error_msg = f"❌ 處理失敗：{str(e)}"
        print("Error:", e)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=error_msg)
        )


# ====== 處理文字訊息（可選）=====
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="請上傳一張包含行事曆的圖片，我會幫你自動建立事件！")
    )


# ====== 啟動伺服器 ======
if __name__ == "__main__":
    print("Starting Line Bot server on http://127.0.0.1:8000")
    app.run(host="127.0.0.1", port=8000, debug=True)