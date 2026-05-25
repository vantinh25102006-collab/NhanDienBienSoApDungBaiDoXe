# Dataset huấn luyện (cho KNN ký tự)

Project dùng pipeline OpenCV classic + `DetectChars.py` train KNN từ:
- `classifications.txt` (mỗi dòng là mã ASCII của ký tự)
- `flattened_images.txt` (mỗi dòng là vector float của ảnh ký tự đã resize về 20x30)

Cách tạo dataset đúng chuẩn trong project này:

## 1) Lưu ảnh biển số đúng label
Từ UI: khi nhận diện sai, bạn nhập biển số đúng và nhấn “Save training sample”.
Hệ thống sẽ lưu:
- ảnh gốc biển số (hoặc ảnh đã upload)
- label plate đúng

## 2) Cắt ký tự & xuất train files
Sau khi đã có đủ ảnh + label, bạn chạy script tạo:
- `classifications.txt`
- `flattened_images.txt`

Script hiện tại **chưa được tạo** trong repo này.

## 3) Huấn luyện / cập nhật
Sau khi tạo xong 2 file train, bạn thay/ghi đè vào repo root:
- `classifications.txt`
- `flattened_images.txt`

và chạy lại app.

