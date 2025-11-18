import re
import datetime
import calendar

CLASS_DICT = {
    "BC": {"start_hour": "08:00:00"},
    "DB": {"start_hour": "10:00:00"},
    "JB": {"start_hour": "16:00:00"},
    "RA": {"start_hour": "23:50:00"},
    "OFF": {"start_hour": "00:00:00"},
    "11FBC": {"start_hour": "08:00:00"},
    "11FDB": {"start_hour": "10:00:00"},
    "11FJB": {"start_hour": "16:00:00"},
    "11FRA": {"start_hour": "00:00:00"},
}


def load_json():
    import json

    with open("ocr_result/2025_09.json", "r", encoding="utf-8") as file:
        data = json.load(file)
    texts = data["description"]

    return texts


def text_to_calender_event_dict(texts):
    """
    ocr 後，處理文字轉換為日曆事件列表提供google calender api 使用
    data = {
        "description1": "11:05\n7Я, 2025 ✓\n+\nIll 4G 964\n=\nBC 7\nJB 1\nOff 8\nDB 3\n11FBC 12\n剩餘年假 0\n30 週一 1週二 2週三 3 週四\n11FBC 11FBC| 11FBC |11FBC\n4週五\n5週六\n6 週日\nOff\n炎上\n11FBC 11FBC\n計價盤點\n7\n8\n9\n11FBC 11FBC |11FBC\n|小暑\n14\nBC\n15\n11FBC\n16\nBC\n11FBC\n10\n11\nOff\n「烏紗 12:3\n17\n18\n11FBC\nOff\nBLS14:3\n12\nOff\n13\nDB\n19\nOff\n20\n11FBC\n21\nBC\n22\nDB\n|大暑\n23\nBC\n24\nBC\n25\nOff\n26\nDB\n27\nBC\n28\nJB\n29\nOff\n30\nOff\n31\n4\nOff\n圓山\n5\nOff\n6\n00\nBC\n1\nBC\n2\nBC\n張有事\n3\nBC\n7\nBC\n8\n9\nDB\nBC\n立秋 父親節\n88\n10\nBC\nDB",
        "description2": "11:05 1\n8Я, 2025\n+\nIll 4G 974\n=\nBC 9\nJB 4\nOff 4\nDB 3\n剩餘年假 0\n28 週一\n29 週二\n30 週三\n31 週四\n1週五\n2週六\n3 週日\nJB\nOff\nOff\nBC\nBC\nBC\nBC\n張有事\n4\nOff\n圓山\n5\nOff\n6\nBC\n7\nBC\n8\nDB\n9\nBC\n立秋\n父親節\n10\nDB\n11\nOff\n12\nBC\n13\nJB\n14\nJB\n15\nJB\n16\nJB\n17\nOff\n展覽\n18\nDB\n19\nBC\n20\nBC\n25\n26\n24\n21\n22\n23\n24\n12\n27\n28\n29\n1\n2\n3\n4\n「軍人節\n處暑\n30\n30\nLO\n5\n6\n7\n祖父母節\n31\n中元節\n囍宴 14:3~\nAD\nP Unlock exclusive features.\n00",
    }

    texts = load_json()
    """

    year, month = get_year_month(texts)

    # 該月1號
    weekday_number = get_weekday_of_first_day(year, month)

    # 該月的天數
    num_days = calendar.monthrange(year, month)[1]

    all_class_list = get_all_class_list(texts)

    current_class_list = all_class_list[weekday_number : weekday_number + num_days]

    if len(current_class_list) > num_days:

        print("警告: 班別數量大於該月天數!")

    calender_event_dict = create_calender_event_dict(year, month, current_class_list)

    return year, month, calender_event_dict


def get_year_month(string):

    string = string.replace(" ", "")
    date_pattern1 = r"(\d+)Я,(\d+)"
    date_pattern2 = r"(\d+)A,(\d+)"

    match = re.search(date_pattern1, string)
    if match:
        month = int(match.group(1))
        year = int(match.group(2))
        print(f"班表年份和月份: {year}年{month}月")

        return year, month

    match = re.search(date_pattern2, string)

    if match:

        month = int(match.group(1))
        year = int(match.group(2))
        print(f"班表年份和月份: {year}年{month}月")

        return year, month

    raise ValueError("無法從字串中解析出年份和月份")


def get_weekday_of_first_day(year, month):
    # 建立該月1號的日期物件
    first_day = datetime.date(year, month, 1)
    # weekday() 回傳 0=星期一, 1=星期二, ..., 6=星期日
    weekday_num = first_day.weekday()

    return weekday_num


def get_all_class_list(texts):

    all_class_list = []

    text_list = texts.split("\n")

    keyword = "剩餘年假"

    start_index = None
    for i, item in enumerate(text_list):
        item = item.replace(" ", "")
        if keyword in item:
            start_index = i + 1  # 取「之後」的元素
            break

    filter_text_list = text_list[start_index:]

    keywords = list(CLASS_DICT.keys())

    # 建立 regex pattern：匹配任一 keyword（支援大小寫）
    # 使用 re.escape 避免特殊字符問題，並按長度排序（避免短 keyword 先匹配）
    sorted_keywords = sorted(
        keywords, key=len, reverse=True
    )  # 長的先匹配，避免 BC 先於 11FBC匹配
    # 使用詞邊界，並對每個關鍵字進行轉義
    pattern = r"\b(?:" + "|".join(re.escape(k) for k in sorted_keywords) + r")\b"
    regex = re.compile(pattern, re.IGNORECASE)

    for i, line in enumerate(filter_text_list):
        matches = regex.findall(line)  # 找出所有匹配的 keyword
        if matches:
            # 轉成大寫或原樣保留都可以
            matches = [m.upper() for m in matches]  # 統一格式

            all_class_list.extend(matches)

    return all_class_list


def create_calender_event_dict(year, month, current_class_list):
    calender_event_dict = {}

    for index, daily_class in enumerate(current_class_list):

        event_dict = {
            "summary": daily_class,
            "start": {"timeZone": "Asia/Taipei"},
            "end": {"timeZone": "Asia/Taipei"},
        }

        start_date = index + 1

        start_hour = int(CLASS_DICT[daily_class]["start_hour"].split(":")[0])

        start_minute = int(CLASS_DICT[daily_class]["start_hour"].split(":")[1])

        start_second = int(CLASS_DICT[daily_class]["start_hour"].split(":")[2])

        start_dt = datetime.datetime(
            year, month, start_date, start_hour, start_minute, start_second
        )

        if daily_class == "OFF":

            formatted_start_dt = start_dt.strftime("%Y-%m-%d")

            end_dt = start_dt + datetime.timedelta(days=1)

            formatted_end_dt = end_dt.strftime("%Y-%m-%d")

            event_dict["start"]["date"] = formatted_start_dt

            event_dict["end"]["date"] = formatted_end_dt

        else:

            formatted_start_dt = start_dt.strftime("%Y-%m-%d %H:%M:%S")

            end_dt = start_dt + datetime.timedelta(hours=8)

            formatted_end_dt = end_dt.strftime("%Y-%m-%d %H:%M:%S")

            event_dict["start"]["dateTime"] = formatted_start_dt.replace(" ", "T")

            event_dict["end"]["dateTime"] = formatted_end_dt.replace(" ", "T")

        date_key = start_dt.strftime("%Y-%m-%d")

        calender_event_dict[date_key] = event_dict

    return calender_event_dict


def roster_message(year, month, calender_event_dict):

    reply_lines = [f"📅 {year}年{month}月 班表如下："]

    sorted_dates = sorted(calender_event_dict.keys())

    for i in range(0, len(sorted_dates), 2):
        date_key1 = sorted_dates[i]
        day1 = date_key1.split("-")[2]
        daily_class1 = calender_event_dict[date_key1].get("summary", "無法識別的班別")

        line = f"{day1}日: {daily_class1}"

        # 檢查是否還有下一筆
        if i + 1 < len(sorted_dates):
            date_key2 = sorted_dates[i + 1]
            day2 = date_key2.split("-")[2]
            daily_class2 = calender_event_dict[date_key2].get(
                "summary", "無法識別的班別"
            )
            line += f" | {day2}日: {daily_class2}"

        reply_lines.append(line)

    return "\n".join(reply_lines)
