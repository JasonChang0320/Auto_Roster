import os.path
import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
import json

# 如果修改了授權範圍，請刪除 token.json 檔案
# 這是為了確保每次都重新進行授權流程
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# 獲取當前檔案的絕對路徑
current_file_path = os.path.abspath(__file__)
print("當前檔案路徑:", current_file_path)

# 獲取當前檔案所在的目錄
current_directory = os.path.dirname(current_file_path)

user_credential_folder = f"{current_directory}/user_credentials"


def authenticate_google_calendar():
    creds = None
    # token.json 儲存了使用者的存取和刷新令牌，在第一次成功授權後自動建立
    if os.path.exists(f"{current_directory}/token.json"):
        creds = Credentials.from_authorized_user_file(
            f"{current_directory}/token.json", SCOPES
        )
    # 如果沒有有效的憑證或憑證已過期，則執行登入流程
    if not creds or not creds.valid:

        # client_secret.json 是你從 Google Cloud Console 下載的憑證檔案
        flow = InstalledAppFlow.from_client_secrets_file(
            f"{current_directory}/client_secret_desktop.json", SCOPES
        )
        creds = flow.run_local_server(port=0)
        # 將憑證儲存起來以供下次使用
        with open(f"{current_directory}/token.json", "w") as token:
            token.write(creds.to_json())
    return creds


def load_OAuth_credentials(user_id):

    creds = Credentials.from_authorized_user_file(
        f"{user_credential_folder}/{user_id}.json", SCOPES
    )

    return creds


def save_OAuth_credentials(user_id, creds):

    cred_path = os.path.join(user_credential_folder, f"{user_id}.json")

    with open(cred_path, "w") as token:
        token.write(creds.to_json())


def get_flow(redirect_uri):

    oauth_credentials_json = os.get_env("GOOGLE_OAUTH_CREDENTIALS")

    if oauth_credentials_json:
        credentials_dict = json.loads(oauth_credentials_json)
        print("✅ 使用 JSON 環境變數建立 OAuth Flow")

        flow = Flow.from_client_config(client_config=credentials_dict, scopes=SCOPES)
    else:
        flow = Flow.from_client_secrets_file(
            f"{current_directory}/client_secret.json",
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
    return flow


def OAuth_user_credential_is_valid(user_id):
    """
    判斷user憑證不存在或過期
    """
    try:
        cred_path = os.path.join(user_credential_folder, f"{user_id}.json")

        if not os.path.exists(cred_path):
            return False

        else:
            creds = Credentials.from_authorized_user_file(
                f"{user_credential_folder}/{user_id}.json", SCOPES
            )

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # 將更新後的憑證儲存起來以供下次使用
                with open(cred_path, "w") as token:
                    token.write(creds.to_json())
                return True
            else:
                return False

        return True
    except Exception as e:
        print(f"檢查憑證有效性時發生錯誤: {e}")
        return False


def get_events_in_month(service, calendar_id="primary", year=None, month=None):
    """獲取指定月份的所有事件"""
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month

    # 設定月份開始和結束時間
    start_date = datetime.datetime(year, month, 1) - datetime.timedelta(hours=8)
    if month == 12:
        next_month = datetime.datetime(year + 1, 1, 1)

    else:
        next_month = datetime.datetime(year, month + 1, 1)

    end_date = next_month - datetime.timedelta(hours=8)

    time_min = start_date.isoformat() + "Z"
    time_max = end_date.isoformat() + "Z"

    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    return events_result.get("items", [])


def get_current_month_ocr_events(service, calendar_id="primary", year=None, month=None):
    """獲取當月所有由ocr_service創建的事件，返回以開始日期為key的字典"""

    # 獲取該月份所有事件
    all_events = get_events_in_month(service, calendar_id, year, month)

    # 篩選出由ocr_service創建的事件，並按日期分組
    ocr_event_dict = {}

    for event in all_events:
        extended_props = event.get("extendedProperties", {}).get("private", {})
        if extended_props.get("created_by") != "ocr_service":
            continue

        if extended_props.get("creation_method") != "ocr":
            continue

        # 提取開始日期作為key
        start = event.get("start", {})
        start_time = start.get("dateTime") or start.get("date", "")

        # 處理日期格式
        if "T" in start_time:
            # dateTime 格式: 2024-01-15T08:00:00+08:00
            date_key = start_time.split("T")[0]
        else:
            # date 格式: 2024-01-15
            date_key = start_time

        # 該日期應該只能有一個事件
        if date_key in ocr_event_dict:
            print(f"{date_key}的事件已存在")
            continue

        ocr_event_dict[date_key] = event

    total_events = len(ocr_event_dict.keys())
    print(f"找到 {total_events} 個由ocr_service創建的事件")
    print(f"涉及 {len(ocr_event_dict)} 個日期")

    return ocr_event_dict


def update_exist_ocr_events(service, current_event_dict, new_event_dict):

    to_create_event_list = []

    for date, new_event in new_event_dict.items():

        current_date_event_dict = current_event_dict.get(date, None)

        if current_date_event_dict == None:

            to_create_event_list.append(new_event)

            continue
        if current_date_event_dict.get("summary") == new_event.get("summary"):

            continue

        update_date_event_dict = current_date_event_dict.copy()

        update_date_event_dict["summary"] = new_event["summary"]
        update_date_event_dict["start"] = new_event["start"]
        update_date_event_dict["end"] = new_event["end"]

        try:
            updated_event = (
                service.events()
                .update(
                    calendarId="primary",
                    eventId=update_date_event_dict["id"],
                    body=update_date_event_dict,
                )
                .execute()
            )

            print(f"✓ 成功新增事件")
            print(f"更新前:{current_date_event_dict['summary']}")
            print(f"更新後:{update_date_event_dict['summary']}")

        except Exception as e:

            print(f"✗ 更新事件失敗: {e}")

    return to_create_event_list


def create_new_event(service, to_create_event):

    if "extendedProperties" not in to_create_event:
        to_create_event["extendedProperties"] = {"private": {}, "shared": {}}  # 可選

    to_create_event["extendedProperties"]["private"].update(
        {
            "created_by": "ocr_service",
            "creation_method": "ocr",
            "created_at": datetime.datetime.now().isoformat(),
            "version": "1.0",
        }
    )

    try:
        # 執行新增操作
        created_event = (
            service.events()
            .insert(calendarId="primary", body=to_create_event)
            .execute()
        )

        print(f"✓ 成功新增事件: {created_event.get('summary', '無標題')}")
        return created_event

    except Exception as e:
        print(f"✗ 新增事件失敗: {e}")


def create_events_in_calendar(year, month, new_event_dict, service):
    """
    year = 2025
    month = 9

    new_event_dict = calender_event_dict # key: date, value: event
    """
    if service == None:
        creds = authenticate_google_calendar()

        service = build("calendar", "v3", credentials=creds)

    current_event_dict = get_current_month_ocr_events(
        service, calendar_id="primary", year=year, month=month
    )

    to_create_event_list = update_exist_ocr_events(
        service, current_event_dict, new_event_dict
    )

    count = 0
    for event in to_create_event_list:

        create_new_event(service, event)

        # count += 1

        # if count > 10:
        #     print("已新增10個事件，停止新增")
        #     break
