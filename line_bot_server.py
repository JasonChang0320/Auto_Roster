from flask import Flask, request, abort, url_for
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
    QuickReply,
    QuickReplyButton,
    MessageAction,
)
from werkzeug.middleware.proxy_fix import ProxyFix

from googleapiclient.discovery import build

if os.path.exists(".env"):
    print(".env 檔案存在，使用.env 環境變數")

    from dotenv import load_dotenv

    load_dotenv(".env")

# ====== 自訂模組 ======
from ocr.ocr_utils import image_to_text
from ocr.process_text import text_to_calender_event_dict, roster_message
from auto_calendar.calendar_utils import (
    create_events_in_calendar,
    OAuth_user_credential_is_valid,
    load_OAuth_credentials,
    save_OAuth_credentials,
    get_flow,
)

# from linebot_config import CHANNEL_ACCESS_TOKEN, CHANNEL_SECRET


CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")

CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
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
line_bot_api = LineBotApi(channel_access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 儲存使用者上傳圖片後，待確認是否建立行事曆事件的暫存資料
pending_ocr_dict = {}


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

    if user_id in pending_ocr_dict.keys():
        del pending_ocr_dict[user_id]

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
        # 下載圖片（不儲存到磁碟，直接用 bytes 處理）
        message_content = line_bot_api.get_message_content(message_id)
        content_bytes = b""
        for chunk in message_content.iter_content():
            content_bytes += chunk

        # 呼叫OCR 處理流程（直接傳 bytes）
        texts = image_to_text(content_bytes)
        year, month, new_event_dict = text_to_calender_event_dict(texts)

        pending_ocr_dict[user_id] = {
            "year": year,
            "month": month,
            "event_dict": new_event_dict,
            "service": service,
        }

        reply_text = roster_message(year, month, new_event_dict)

        reply_msg = TextSendMessage(
            text=f"OCR 辨識結果如下，請問是否要將此班表新增至您的 Google 行事曆？\n\n{reply_text}",
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(
                        action=MessageAction(label="✅ 同意", text="同意")
                    ),
                    QuickReplyButton(
                        action=MessageAction(label="❌ 不同意", text="不同意")
                    ),
                ]
            ),
        )

        line_bot_api.reply_message(event.reply_token, reply_msg)

        return

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
            <body style="font-family: Arial, sans-serif; padding: 30px; font-size: 18px; line-height: 1.6;">
                <h2 style="font-size: 28px; color: #2e7d32;">✅ 授權成功！</h2>
                <p>你現在可以回到 LINE，上傳行事曆圖片，Bot 會自動幫你建立事件。</p>
                <p><small style="font-size: 14px; color: #666;">此頁面可關閉。</small></p>
            </body>
        </html>
        """
    except Exception as e:
        print("OAuth Error:", e)
        return f"❌ 授權失敗：{str(e)}", 500


# ====== 處理文字訊息（可選）=====
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_id = event.source.user_id
    text = event.message.text

    if text == "同意" and user_id in pending_ocr_dict.keys():

        try:
            # 回覆成功訊息
            reply_text = "正在將班表新增至您的 Google 行事曆，請稍候..."
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=reply_text)
            )
            create_events_in_calendar(
                pending_ocr_dict[user_id]["year"],
                pending_ocr_dict[user_id]["month"],
                pending_ocr_dict[user_id]["event_dict"],
                pending_ocr_dict[user_id]["service"],
            )

            # 回覆成功訊息
            success_text = "✅ 已成功將班表新增至您的 Google 行事曆！"
            line_bot_api.push_message(
                to=event.source.user_id, messages=TextSendMessage(text=success_text)
            )

        except Exception as e:
            error_msg = f"❌ 建立行事曆事件失敗：{str(e)}"
            print("Error:", e)
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=error_msg)
            )
        finally:
            # 刪除已處理的待確認資料
            del pending_ocr_dict[user_id]

    elif text == "不同意" and user_id in pending_ocr_dict.keys():
        # 使用者不同意，刪除待確認資料
        del pending_ocr_dict[user_id]
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="已取消班表新增。如需再次上傳圖片，請重新傳送。"),
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請上傳一張包含行事曆的圖片，我會幫你自動建立事件！"),
        )

    if user_id in pending_ocr_dict.keys():

        del pending_ocr_dict[user_id]


# ====== 啟動伺服器 ======
if __name__ == "__main__":
    print("Starting Line Bot server on http://127.0.0.1:8000")
    app.run(host="127.0.0.1", port=8000, debug=True)
