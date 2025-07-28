from google.cloud import vision
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
import base64
from ocr.ocr_config import ALLOWED_EXTENSIONS
import os


def is_allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def get_target_image(file):

    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    if not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=400, detail="File type not allowed. Only images are accepted."
        )

    # 儲存圖片到本地
    folder_name = "./ocr/tmp_images"

    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"資料夾 '{folder_name}' 已建立")
    else:
        print(f"資料夾 '{folder_name}' 已存在")

    try:
        file_path = f"{folder_name}/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save failed: {e}")

    return file_path


def image_to_text(path):
    """Detects text in the file."""

    key_path = "./ocr/ocr_key.json"  # ← 改成你的實際路徑
    ocr_path = "./ocr/ocr_result"

    if not os.path.exists(ocr_path):
        os.makedirs(ocr_path)
        print(f"資料夾 '{ocr_path}' 已建立")
    else:
        print(f"資料夾 '{ocr_path}' 已存在")

    client = vision.ImageAnnotatorClient.from_service_account_json(key_path)

    with open(path, "rb") as image_file:
        content = image_file.read()

    filename = os.path.basename(path)

    image = vision.Image(content=content)

    response = client.text_detection(image=image)
    texts = response.text_annotations

    if texts:
        # print(texts[0].description)

        with open(
            os.path.join(ocr_path, f"{filename.split(".")[0]}.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                {"description": texts[0].description}, f, ensure_ascii=False, indent=2
            )

    else:
        print("沒有偵測到文字")

    if response.error.message:
        raise Exception(
            "{}\nFor more info on error messages, check: "
            "https://cloud.google.com/apis/design/errors".format(response.error.message)
        )
    return texts[0].description
