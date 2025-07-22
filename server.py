from fastapi import FastAPI, UploadFile, File, HTTPException, Form
import os
import nest_asyncio
import asyncio
from uvicorn import Config, Server
from ocr.ocr_utils import get_target_image, image_to_text

from auto_calendar.calendar_utils import create_events_in_calendar


app = FastAPI()


@app.post("/settup-schedule/")
async def settup_schedule(file: UploadFile = File(...), code: str = Form()):

    file_path = get_target_image(file)

    print(file_path)
    texts = image_to_text(file_path)

    # response = create_events_in_calendar(texts, code)

    return file_path


# 解決 event loop 衝突問題
nest_asyncio.apply()


# 啟動 FastAPI 伺服器
async def run_server():
    config = Config(app=app, host="127.0.0.1", port=8000, loop="asyncio")
    server = Server(config)
    await server.serve()


# 執行伺服器
asyncio.run(run_server())
