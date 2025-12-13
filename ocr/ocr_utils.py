from google.cloud import vision
import os
import cv2
import numpy as np

# 獲取當前檔案的絕對路徑
current_file_path = os.path.abspath(__file__)

# 獲取當前檔案所在的目錄
current_directory = os.path.dirname(current_file_path)

# KEY_PATH = os.path.join(current_directory, "ocr_key.json")

OCR_CREDENTIAL_DICT = {
    "type": os.getenv("OCR_TYPE"),
    "project_id": os.getenv("OCR_PROJECT_ID"),
    "private_key_id": os.getenv("OCR_PRIVATE_KEY_ID"),
    "private_key": os.getenv("OCR_PRIVATE_KEY"),
    "client_email": os.getenv("OCR_CLIENT_EMAIL"),
    "client_id": os.getenv("OCR_CLIENT_ID"),
    "auth_uri": os.getenv("OCR_AUTH_URI"),
    "token_uri": os.getenv("OCR_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("OCR_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("OCR_CLIENT_X509_CERT_URL"),
    "universe_domain": os.getenv("OCR_UNIVERSE_DOMAIN"),
}


def image_to_text(image_bytes: bytes):
    """Detects text in the given image bytes.

    `image_bytes` must be raw bytes (bytes or bytearray). Provide an optional
    `filename` to use when saving the OCR JSON (defaults to a timestamp-based name).
    """

    if not isinstance(image_bytes, (bytes, bytearray)):
        raise TypeError("image_to_text requires image bytes (bytes or bytearray)")

    # client = vision.ImageAnnotatorClient.from_service_account_json(KEY_PATH)
    try:
        client = vision.ImageAnnotatorClient.from_service_account_info(
            OCR_CREDENTIAL_DICT
        )
    except Exception as e:
        raise Exception(f"無法建立 Google Vision 客戶端: {e}")

    content = bytes(image_bytes)

    image = vision.Image(content=content)

    response = client.document_text_detection(image=image)

    # plot_predict_result(response, image_file_path)

    sorted_lines_dict, sorted_text = get_sorted_context(response)

    # plot_sorted_result(sorted_lines_dict, image_file_path)

    if sorted_lines_dict == {}:

        print("沒有偵測到文字")

    if getattr(response, "error", None) and getattr(response.error, "message", None):
        raise Exception(
            "{}\nFor more info on error messages, check: "
            "https://cloud.google.com/apis/design/errors".format(response.error.message)
        )

    return sorted_text


def get_sorted_context(response):
    sorted_text = ""
    # 收集所有 word + 座標 + 文字
    words_with_coords = []

    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    word_text = "".join([s.text for s in word.symbols])
                    # 取 bounding box 左上角作為排序基準
                    x = word.bounding_box.vertices[0].x
                    y = word.bounding_box.vertices[0].y
                    words_with_coords.append(
                        {
                            "text": word_text,
                            "x": x,
                            "y": y,
                            "vertices": [
                                (v.x, v.y) for v in word.bounding_box.vertices
                            ],
                        }
                    )

    # 排序：先按 y（行），再按 x（列）→ 由上到下，由左到右
    # 設定容忍誤差（同一行 y 差異小於 threshold 視為同行）
    Y_THRESHOLD = 5

    # 分群：把相近 y 的字歸為同一「行」
    sorted_lines_dict = {}
    for w in words_with_coords:
        y = w["y"]
        # 找到最接近的行（y 在 ±threshold 內）
        found_line = None
        for line_y in sorted_lines_dict.keys():
            if abs(y - line_y) <= Y_THRESHOLD:
                found_line = line_y
                break
        if found_line is None:
            sorted_lines_dict[y] = []
        else:
            # 歸到已存在的行（使用該行的 key）
            sorted_lines_dict[found_line].append(w)
            continue
        sorted_lines_dict[y].append(w)

    # 每行內按 x 排序
    for y, words_info in sorted_lines_dict.items():
        sorted_lines_dict[y] = sorted(words_info, key=lambda w: w["x"])

    # 輸出最終排序文字
    # print("=== 由上到下、由左到右的文字順序 ===")
    for i, y in enumerate(sorted(sorted_lines_dict.keys())):
        word_info_list = sorted_lines_dict[y]
        line_text = " ".join([w["text"] for w in word_info_list])
        sorted_text += line_text + "\n"
        print(f"第 {i+1} 行: {line_text}")

    return sorted_lines_dict, sorted_text


def plot_predict_result(response, image_file_path):
    OCR_PATH = f"{current_directory}/ocr_result"
    # 載入原始圖片
    img = cv2.imread(image_file_path)

    # 確保圖片成功載入
    if img is None:
        raise FileNotFoundError(f"無法載入圖片: {image_file_path}")

    # 遍歷所有文字框並畫框
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    # 取得文字內容
                    word_text = "".join([symbol.text for symbol in word.symbols])
                    # 取得四個頂點座標
                    vertices = [
                        (vertex.x, vertex.y) for vertex in word.bounding_box.vertices
                    ]

                    # OpenCV 使用 (x, y) 座標，順序為左上、右上、右下、左下（Google Vision 通常也是這個順序）
                    pts = np.array(vertices, np.int32)
                    pts = pts.reshape((-1, 1, 2))

                    # 畫多邊形框（綠色，粗細 2）
                    cv2.polylines(
                        img, [pts], isClosed=True, color=(0, 255, 0), thickness=2
                    )

                    # （可選）在框左上角標示文字（小字）
                    if vertices:
                        x, y = vertices[0]  # 左上角
                        cv2.putText(
                            img,
                            word_text,
                            (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (255, 0, 0),
                            1,
                        )

    # 顯示圖片
    # cv2.imshow("OCR Result", img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    # 或儲存結果圖片
    file_name = image_file_path.split("/")[-1].split(".")[0] + "_ocr.jpg"
    path = os.path.join(OCR_PATH, file_name)
    cv2.imwrite(path, img)


def plot_sorted_result(sorted_lines_dict, image_file_path):
    OCR_PATH = f"{current_directory}/ocr_result"
    img = cv2.imread(image_file_path)
    for i, y in enumerate(sorted(sorted_lines_dict.keys())):
        word_info_list = sorted_lines_dict[y]
        for j, w in enumerate(word_info_list):
            x, y = w["vertices"][0]
            cv2.putText(
                img,
                f"{i+1}-{j+1}",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1,
            )
            cv2.polylines(
                img,
                [np.array(w["vertices"], np.int32).reshape(-1, 1, 2)],
                True,
                (0, 255, 0),
                1,
            )

    file_name = image_file_path.split("/")[-1].split(".")[0] + "_sorted.jpg"
    path = os.path.join(OCR_PATH, file_name)
    cv2.imwrite(path, img)
