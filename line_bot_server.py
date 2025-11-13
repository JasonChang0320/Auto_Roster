from flask import Flask, request, abort, url_for, redirect
import os
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    ImageMessage,
    TextSendMessage,
    TemplateSendMessage,
    ButtonsTemplate,
    URIAction,
)
from werkzeug.middleware.proxy_fix import ProxyFix

from googleapiclient.discovery import build

# ====== 你的原有模組 ======
from ocr.ocr_utils import image_to_text
from ocr.process_text import text_to_calender_event_dict
from auto_calendar.calendar_utils import (
    create_events_in_calendar,
    OAuth_user_credential_is_valid,
    load_OAuth_credentials,
    save_OAuth_credentials,
    get_flow,
)
from linebot_config import CHANNEL_ACCESS_TOKEN, CHANNEL_SECRET

# ====== 設定 ======
app = Flask(__name__)

# 信任來自 proxy 的 X-Forwarded-* headers
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,  # 信任 1 層 X-Forwarded-For
    x_proto=1,  # 信任 X-Forwarded-Proto（用來判斷 https）
    x_host=1,  # 信任 X-Forwarded-Host（用來取得正確 host）
    x_prefix=1,  # 如果有 X-Forwarded-Prefix
)
# =====記得更新======
# linebot 上的 webhook url
# google ocr_calendar 的callback url
# =================

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
        if OAuth_user_credential_is_valid(user_id) == False:

            redirect_uri = url_for("google_oauth_callback", _external=True)
            redirect_uri = redirect_uri.replace("http://", "https://")
            flow = get_flow(redirect_uri)

            authorization_url, state = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                state=user_id,
                prompt="consent",  # 強制使用者重新同意，確保 refresh_token
            )
            buttons_template_message = TemplateSendMessage(
                alt_text="按鈕訊息",
                template=ButtonsTemplate(
                    title="Google 行事曆授權",
                    text="請點擊下方按鈕，在瀏覽器中完成授權流程",
                    actions=[URIAction(label="開啟授權頁面", uri=authorization_url)],
                ),
            )

            line_bot_api.reply_message(
                event.reply_token,
                buttons_template_message,
            )

            return

        # 建立 Google Calendar 服務
        credentials = load_OAuth_credentials(user_id)

        service = build("calendar", "v3", credentials=credentials)
        # 下載圖片
        message_content = line_bot_api.get_message_content(message_id)
        file_path = os.path.join(UPLOAD_FOLDER, f"{message_id}.jpg")
        with open(file_path, "wb") as f:
            for chunk in message_content.iter_content():
                f.write(chunk)

        # 呼叫你的 OCR 處理流程
        texts = image_to_text(file_path)
        year, month, new_event_dict = text_to_calender_event_dict(texts)

        create_events_in_calendar(year, month, new_event_dict, service)

        # 回覆成功訊息
        reply_text = (
            "✅ 已成功解析圖片並建立行事曆事件！\n"
            f"偵測文字：\n{texts[:100]}..."  # 避免太長
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    except Exception as e:
        error_msg = f"❌ 處理失敗：{str(e)}"
        print("Error:", e)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=error_msg))




@app.route("/google/oauth/callback")
def google_oauth_callback():
    """
    Google 授權完成後的回調路由
    """
    state = request.args.get("state")  # 這裡就是 LINE user_id
    print(state)
    if not state:
        return "❌ 錯誤：無法識別使用者", 400

    # 讀取對應的 flow
    try:
        redirect_uri = url_for("google_oauth_callback", _external=True)
        # 將 request.url 的協議改為 https
        # 因為 ngrok 用 HTTPS，但 Flask 看到的是 HTTP
        authorization_response = request.url
        if authorization_response.startswith("http://"):
            authorization_response = (
                "https://" + authorization_response[len("http://") :]
            )

        flow = get_flow(redirect_uri)

        flow.fetch_token(authorization_response=authorization_response)

        credentials = flow.credentials

        # 儲存 credentials（用 LINE user_id 當檔名）
        save_OAuth_credentials(state, credentials)

        return """
        <html>
          <head><title>授權成功</title></head>
          <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>✅ 授權成功！</h2>
            <p>你現在可以回到 LINE，上傳行事曆圖片，Bot 會自動幫你建立事件。</p>
            <p><small>此頁面可關閉。</small></p>
          </body>
        </html>
        """
    except Exception as e:
        print("OAuth Error:", e)
        return f"❌ 授權失敗：{str(e)}", 500


# ====== 處理文字訊息（可選）=====
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="請上傳一張包含行事曆的圖片，我會幫你自動建立事件！"),
    )


# ====== 啟動伺服器 ======
if __name__ == "__main__":
    print("Starting Line Bot server on http://127.0.0.1:8000")
    app.run(host="127.0.0.1", port=8000, debug=True)
