# TODO

## Phase 1 - Backend API
- [x] Xem code hiện tại: `app.py`, `parking/service.py`, `parking/db.py`, `templates/index.html`.
- [x] Thêm endpoint `POST /recognize` để nhận diện biển số ngay khi upload ảnh.
- [x] Thêm endpoint `GET /active` để trả danh sách xe đang đỗ.
- [x] Thêm DB/service method `get_active_vehicles()`.

## Phase 2 - Frontend UI/UX

- [ ] Viết lại `templates/index.html` theo layout mới:
  - [ ] 1 ô Plate + 1 upload ảnh
  - [ ] Toggle nút đổi chế độ Check-in / Check-out
  - [ ] Tự fill plate khi upload + khóa ô
  - [ ] Nút Check-in/Check-out gửi dữ liệu
  - [ ] Bảng "xe đang đỗ" + bảng "lịch sử" (gọi `/active`, `/history`)
  - [ ] Hiển thị thời gian chi tiết khi check-in/out

## Phase 3 - Fix lỗi nhận diện
- [ ] Đảm bảo upload kích hoạt recognize liền; không phụ thuộc việc gõ ký tự.
- [ ] Khi đã auto-fill và khóa, chỉ nhận lại khi upload ảnh mới (hoặc cơ chế cho phép unlock theo thiết kế).

## Phase 4 - Test
- [ ] Chạy Flask và test theo luồng: upload → auto fill → check-in → check-out → load bảng.

