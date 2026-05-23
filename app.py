from __future__ import annotations

import base64
import io
import os
from datetime import datetime

from flask import Flask, jsonify, request, render_template

import Main
from parking.service import ParkingService


app = Flask(__name__)

service = ParkingService(
    db_path=os.path.join(os.path.dirname(__file__), "parking.db"),
)


def _save_upload_image_to_tmp(file_storage) -> str:
    # Store to a temp file inside repo for compatibility with existing OpenCV code
    tmp_dir = os.path.join(os.path.dirname(__file__), "tmp_uploads")
    os.makedirs(tmp_dir, exist_ok=True)

    filename = f"upload_{int(datetime.now().timestamp())}.png"
    path = os.path.join(tmp_dir, filename)
    file_storage.save(path)
    return path


@app.post("/check-in")
def check_in():
    payload = request.form if request.form else request.json or {}

    plate = payload.get("plate")
    image_file = request.files.get("image") if request.files else None

    if not image_file and not plate:
        return jsonify({"error": "Missing plate or image"}), 400

    # Ưu tiên nhận diện từ ảnh nếu có; nếu không có ảnh thì lấy từ plate text
    if image_file is not None:
        image_path = _save_upload_image_to_tmp(image_file)
        plate_str = Main.detect_plate_str_from_image(image_path)
    else:
        plate_str = str(plate).strip().upper()

    time_in = datetime.now()


    result = service.check_in(plate_str=plate_str, time_in=time_in)
    return jsonify(result)


@app.post("/check-out")
def check_out():
    payload = request.form if request.form else request.json or {}

    plate = payload.get("plate")
    image_file = request.files.get("image") if request.files else None

    if not plate and not image_file:
        return jsonify({"error": "Missing plate or image"}), 400

    # Ưu tiên nhận diện từ ảnh nếu có; nếu không có ảnh thì lấy từ plate text
    if image_file is not None:
        image_path = _save_upload_image_to_tmp(image_file)
        plate_str = Main.detect_plate_str_from_image(image_path)
    else:
        plate_str = str(plate).strip().upper()

    time_out = datetime.now()


    result = service.check_out(plate_str=plate_str, time_out=time_out)
    if result.get("status") == "error":
        return jsonify(result), 400
    return jsonify(result)


@app.get("/history")
def history():
    rows = service.get_history(limit=200)
    return jsonify({"items": rows})


@app.get("/spots")
def spots():
    spots = service.get_spots()
    return jsonify({"items": spots})


from flask import render_template


@app.get("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


