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
- line-bot-sdk (line-bot-sdk)
- google-cloud-vision
- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib
- opencv-python
- numpy

可用 pip 一次安裝（示範）：

```bat
python -m pip install Flask requests line-bot-sdk google-cloud-vision google-api-python-client google-auth-httplib2 google-auth-oauthlib opencv-python numpy
```

（若想把依賴寫入 `requirements.txt`，可自行生成）

## 設定（必要）

1. Google Cloud Vision service account key

   - 建立或下載 service account JSON（需包含 Vision API 權限），放到 `ocr/ocr_key.json` 路徑下。
   - 檔案名稱與路徑可修改，但需同步調整 `ocr/ocr_utils.py` 的 `KEY_PATH` 或將環境變數改寫碼中讀取位置。

2. Google Calendar OAuth

   - 在 Google Cloud Console 中建立 OAuth 客戶端（桌面應用或 Web），下載 `client_secret.json` 並放到 `auto_calendar/` 資料夾。
   - 程式第一次運行時會在 `auto_calendar/` 資料夾產生 `token.json`，供後續存取（請勿上傳 token 與金鑰到公開 repository）。

3. Line Bot（選用）

   - 在 `linebot_config.py` 中填入自己的 `CHANNEL_ACCESS_TOKEN` 與 `CHANNEL_SECRET`。
   - 若要測試 webhook，需把機器人 webhook 指向可由外部存取的 URL（可使用 ngrok 對本機 8000 暴露）。

4. 私密資訊管理

   - 請將 `ocr/ocr_key.json` 與 `auto_calendar/client_secret.json`、`auto_calendar/token.json`（若存在）視為敏感檔案，勿上傳到公開 Git 倉庫。

## 快速使用

1. 啟動 Flask 上傳 API（本機測試）

```bat
python server.py
```

會在 `http://127.0.0.1:8000/setup-schedule/` 提供一個 POST 上傳點（multipart/form-data，欄位名稱 `file`）。

2. 使用專案內的 client 範例上傳圖片

```bat
python client\client.py
```

`client.py` 會將 `client/client_image/` 中指定的圖片上傳到 `server.py` 的 `/setup-schedule/`，並印出伺服器回傳內容。

3. 或直接啟動 Line Bot server（若已設定 `linebot_config.py`）

```bat
python line_bot_server.py
```

在 Line 上傳圖片後，Bot 會把圖片下載、呼叫 OCR、解析並建立 Google Calendar 事件，最後回覆使用者處理結果文字。

## 解析邏輯概要（OCR -> Calendar）

1. OCR：`ocr/ocr_utils.py` 使用 Google Cloud Vision 的 document_text_detection，將影像中的字以「由上到下、由左到右」排序，並輸出純文字 `sorted_text`。
2. 文字解析：`ocr/process_text.py` 會解析日期（年、月）與從某個關鍵詞（例如 `剩餘年假`）之後的每行班別關鍵字，並依據 `CLASS_DICT` 轉換為事件的起訖時間或整天事件（OFF）。
3. Calendar 建立：`auto_calendar/calendar_utils.py` 會先以 OAuth/credentials 建立 `service`，讀取當月已由 `ocr_service` 建立的事件（以 extendedProperties 判斷），然後比對並更新已存在事件或建立新的事件。

## 常見問題與注意事項

- OCR 質量：圖片品質（解析度、傾斜、雜訊）會直接影響辨識結果。必要時請先對圖片做裁切或預處理。
- 關鍵字與格式：解析器以特定關鍵字（例如 `剩餘年假`）與 `CLASS_DICT` 內的班別為基準，如有不同班別或不同版型，可能需要調整 `ocr/process_text.py` 的正則或 `CLASS_DICT`。
- 權限及 OAuth：第一次使用 Google Calendar API 時會開啟瀏覽器進行授權並產生 `token.json`。若想強制重新授權，可刪除 `auto_calendar/token.json` 再次執行。
- 時區：事件建立使用 `Asia/Taipei` 為時區，若需更換請在 `ocr/process_text.py` 與 `auto_calendar/calendar_utils.py` 中相應修改。

## 測試與驗證

- 可以在 `ocr/ocr_result/` 看到 OCR 結果的 JSON 與標記圖（若有輸出）。
- 使用 `client/client.py` 上傳已知範例圖片，觀察是否於 Google Calendar（primary）中建立正確事件。

## 下一步建議（可選）

- 加入 `requirements.txt` 與範例 `.env` 檔案（或使用 `python-dotenv`）以更好地管理設定與相依性。
- 將 Line Bot webhook 與 server 整合為同一個更完整的部署流程（Docker、Heroku、GCP Run 等）。
- 加強 OCR 前處理（傾斜校正、去雜訊）以提升辨識率。

## 聯絡與授權

作者：請參考 repository 的 commit 或聯絡擁有者。

此 README 為專案操作說明；實作細節請參考各模組來源檔案（例如 `ocr/ocr_utils.py`、`ocr/process_text.py`、`auto_calendar/calendar_utils.py`）。
