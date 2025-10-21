# Auto_Roster

## 專案簡介

Auto_Roster 是一個將班表圖片自動轉換為 Google Calendar 事件的工具。工作流程為：

- 使用 Google Cloud Vision OCR 辨識上傳的班表圖片
- 解析 OCR 結果，轉換為每天的班別（如 BC、DB、JB、OFF、11FBC 等）
- 使用 Google Calendar API 建立（或更新）對應日期的事件，並在 event 的 extendedProperties 裡記錄來源

此專案同時提供一個簡單的 HTTP 上傳端點（`server.py`）供手動上傳圖片處理，還有一個 Line Bot（`line_bot_server.py`）可以讓使用者直接在 Line 上傳圖片自動處理。

## 主要功能

- 圖片上傳 -> OCR 文字擷取（使用 Google Cloud Vision）
- 文字解析成班別清單、轉換為每日日曆事件
- 使用 Google Calendar API 建立/更新事件
- 提供 Flask 的上傳 API（`/setup-schedule/`）與 Line Bot Webhook（`/callback`）範例

![image](https://github.com/JasonChang0320/Auto_Roster/blob/main/image/flow.png)

## 專案結構（重點檔案）

- `server.py` - Flask 上傳 API，透過 POST 上傳圖片並建立日曆事件
- `line_bot_server.py` - Line Bot Webhook server，接收使用者上傳的圖片並處理
- `ocr/ocr_utils.py` - 與 Google Vision 的整合、OCR 處理與影像輸出檔案
- `ocr/process_text.py` - 將 OCR 純文字解析為 calendar event dict 的邏輯
- `auto_calendar/calendar_utils.py` - Google Calendar 認證與事件建立/更新邏輯
- `client/client.py` - 簡單的 client 範例，用來上傳本機圖片到 `server.py`
- `linebot_config.py` - Line Bot 的 CHANNEL_ACCESS_TOKEN / CHANNEL_SECRET（範例放在此檔）
- `auto_calendar/client_secret.json` - Google Calendar OAuth client secret（私密檔，請妥善管理）
- `ocr/ocr_key.json` - Google Cloud Vision service account key（私密檔，請妥善管理）

另外，專案內有多個範例圖片與 OCR 結果：`uploads/`, `client/client_image/`, `ocr/ocr_result/` 等資料夾。

## 需求與相依套件

建議在 Python 3.10+ 的虛擬環境中執行。主要第三方套件（請依需要安裝）：

- Flask
- requests

# Auto_Roster

一個把紙本或圖片班表自動轉成 Google Calendar 事件的工具。它會把上傳的班表圖片送到 Google Cloud Vision 做 OCR，解析出每天的班別（例如 BC、DB、JB、OFF、11FBC），再用 Google Calendar API 建立或更新對應日期的事件。

## 主要功能（簡短）

- OCR 擷取圖片文字並儲存 JSON 結果
- 解析出年、月與每日班別，依班別建立事件（含全天 OFF 的處理）
- 比對同月已有由 OCR 建立的事件，必要時更新或新增
- 提供 Flask 上傳 API (`/setup-schedule/`) 與 Line Bot webhook (`/callback`) 範例

## 快速開始（Windows, cmd.exe）

1. 建立虛擬環境並安裝套件：

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install Flask requests line-bot-sdk google-cloud-vision google-api-python-client google-auth-httplib2 google-auth-oauthlib opencv-python numpy
```

2. 放置必要金鑰檔案：

- 將 Google Cloud Vision service account JSON 放到 `ocr/ocr_key.json`
- 將 Google OAuth client secret（client_secret.json）放到 `auto_calendar/` 資料夾

3. 啟動本機測試 server：

```bat
python server.py
```

上傳端點：POST `http://127.0.0.1:8000/setup-schedule/`，multipart/form-data 欄位名為 `file`。

4. 使用範例 client 上傳圖檔：

```bat
python client\client.py
```

或啟動 Line Bot（已在 `linebot_config.py` 填好 token/secret 且 webhook 可被外界存取）：

```bat
python line_bot_server.py
```

## 環境變數與檔案（重要）

- `ocr/ocr_key.json`：Google Vision service account（金鑰）
- `auto_calendar/client_secret.json`：Google OAuth client secret
- `auto_calendar/token.json`：授權 token（程式會在首次授權時建立）
- `linebot_config.py`：LINE 的 `CHANNEL_ACCESS_TOKEN` 及 `CHANNEL_SECRET`

## 重要檔案說明

- `ocr/ocr_utils.py`：呼叫 Google Vision、整理文字（由上到下、由左到右），並把 OCR JSON 寫到 `ocr/ocr_result/`。
- `ocr/process_text.py`：將 OCR 字串解析出年/月及每日班別（使用 `CLASS_DICT`），並輸出 Google Calendar 可用的 event dict。
- `auto_calendar/calendar_utils.py`：管理 Google Calendar 的認證、讀取當月 OCR 建立的事件、更新或新增事件。
- `server.py`：簡單的 Flask API，接受上傳圖片並執行整個處理流程。
- `line_bot_server.py`：Line webhook 範例，接收圖片、跑 OCR、建立事件並回覆結果。

## 常見問題（快速解答）

- OCR 結果不正確：請先確認圖片解析度、裁切是否只保留班表區域，或加入前處理（去雜訊、校正傾斜）。
- 解析不到年/月或班別：`ocr/process_text.py` 使用簡單的正則與關鍵字匹配，若版型不同需調整 `get_year_month` 或 `CLASS_DICT`。
- 權限問題：若 Google Calendar API 在第一次運行時無法授權，請檢查 `client_secret.json` 是否正確，或刪除 `auto_calendar/token.json` 後重試授權流程。
