from flask import Flask, request, jsonify
import os
from ocr.ocr_utils import get_target_image, image_to_text
from ocr.process_text import text_to_calender_event_dict

from auto_calendar.calendar_utils import create_events_in_calendar

# 初始化 Flask 應用
app = Flask(__name__)

# 設定上傳暫存資料夾
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/setup-schedule/", methods=["POST"])
def setup_schedule():
    # 檢查是否有上傳檔案
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)

    print(f"檔案已儲存到: {file_path}")
    # 使用你的 OCR 工具處理圖片
    try:
        texts = image_to_text(file_path)

        year, month, new_event_dict = text_to_calender_event_dict(texts)

        response = create_events_in_calendar(year, month, new_event_dict, service=None)

        # 回傳結果
        return (
            jsonify(
                {
                    "file_path": file_path,
                    "texts": texts,
                    # 'calendar_response': response
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("Starting Flask server on http://127.0.0.1:8000")
    app.run(host="127.0.0.1", port=8000, debug=True)
