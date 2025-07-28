import os.path
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# 如果修改了授權範圍，請刪除 token.json 檔案
# 這是為了確保每次都重新進行授權流程
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def authenticate_google_calendar():
    creds = None
    # token.json 儲存了使用者的存取和刷新令牌，在第一次成功授權後自動建立
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # 如果沒有有效的憑證或憑證已過期，則執行登入流程
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # client_secret.json 是你從 Google Cloud Console 下載的憑證檔案
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # 將憑證儲存起來以供下次使用
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


# 在你的應用程式中呼叫這個函數來取得憑證
# creds = authenticate_google_calendar()


def create_event(event, creds):
    try:
        service = build("calendar", "v3", credentials=creds)

        # 範例：取得主要日曆上的未來 10 個活動
        print("Getting the upcoming 10 events")
        now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        # 列印活動資訊
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(f"{start} {event['summary']}")

    except HttpError as error:
        print(f"An error occurred: {error}")


def create_events_in_calendar(calender_event_list):

    creds = authenticate_google_calendar()
    for event in calender_event_list:

        create_event(event, creds)

        break
