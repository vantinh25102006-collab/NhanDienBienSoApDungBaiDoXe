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


@app.post("/recognize")
def recognize():
    image_file = request.files.get("image") if request.files else None
    if image_file is None:
        return jsonify({"status": "error", "message": "Missing image"}), 400

    image_path = _save_upload_image_to_tmp(image_file)
    plate_str = Main.detect_plate_str_from_image(image_path)
    return jsonify({"status": "ok", "plate": str(plate_str).strip().upper()})


@app.get("/active")
def active():
    items = service.get_active_vehicles()
    return jsonify({"items": items})


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

    # Lưu đường dẫn ảnh để UI có thể hiển thị lại khi click ô trong sơ đồ
    last_image_path = image_path if image_file is not None else None

    result = service.check_in(
        plate_str=plate_str,
        time_in=time_in,
        last_image_path=last_image_path,
    )
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


@app.post("/active/update-plate")
def active_update_plate():
    payload = request.form if request.form else request.json or {}
    old_plate = payload.get("old_plate")
    new_plate = payload.get("new_plate")

    result = service.update_active_plate(old_plate=old_plate, new_plate=new_plate)
    if result.get("status") == "error":
        return jsonify(result), 400
    return jsonify(result)


@app.post("/active/delete")
def active_delete():
    payload = request.form if request.form else request.json or {}
    plate = payload.get("plate")

    result = service.delete_active_vehicle(plate=plate)
    if result.get("status") == "error":
        return jsonify(result), 400
    return jsonify(result)


@app.post("/history/update-plate")
def history_update_plate():
    payload = request.form if request.form else request.json or {}
    event_id = payload.get("event_id")
    new_plate = payload.get("new_plate")

    result = service.update_history_plate(event_id=event_id, new_plate=new_plate)
    if result.get("status") == "error":
        return jsonify(result), 400
    return jsonify(result)


@app.post("/history/delete")
def history_delete():
    payload = request.form if request.form else request.json or {}
    event_id = payload.get("event_id")

    result = service.delete_history_event(event_id=event_id)
    if result.get("status") == "error":
        return jsonify(result), 400
    return jsonify(result)


@app.get("/tmp_uploads/<path:filename>")
def tmp_uploads(filename: str):

    # Serve stored upload images so UI can display them.
    # Note: we intentionally scope to tmp_uploads folder.
    from flask import send_from_directory

    tmp_dir = os.path.join(os.path.dirname(__file__), "tmp_uploads")
    return send_from_directory(tmp_dir, filename)


from flask import render_template



@app.get("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


