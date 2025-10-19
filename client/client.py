import requests
import time

# 設定上傳的 URL
url = "http://127.0.0.1:8000/setup-schedule/"

# url = "https://1129bead8307.ngrok-free.app/setup-schedule/"

# 指定要上傳的圖片路徑
file_name = "2025_11.jpg"  # 替換成你本地的圖片路徑
file_path = f"./client_image/{file_name}"
# 使用 requests 上傳檔案

try:
    with open(file_path, "rb") as f:
        print(file_name)
        files = {"file": (file_name, f, "image/png")}  # 指定檔名、文件物件與 MIME type
        response = requests.post(url, files=files)

    # 輸出結果
    if response.status_code == 200:
        print("✅ 圖片上傳成功！")
        print(response.json())
    else:
        print(f"❌ 上傳失敗: {response.status_code}")
        print(response.json())

except FileNotFoundError:
    print("找不到指定的圖片檔案，請確認路徑是否正確。")
except requests.exceptions.ConnectionError:
    print("無法連接到伺服器，請確認 FastAPI 服務是否已啟動。")
