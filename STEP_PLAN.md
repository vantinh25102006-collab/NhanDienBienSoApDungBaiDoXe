## Tóm tắt yêu cầu
Cập nhật `templates/index.html` + JS + một ít backend (nếu cần) để:
1) Có 1 ô nhập biển số + 1 upload ảnh. Upload -> nhận diện ngay -> tự điền biển số, khóa ô. Check-in/check-out thông báo lưu/thông tin tồn tại.
2) Có nút toggle chế độ Check-in/Check-out.
3) Có nút danh sách xe đang đổ dạng bảng: plate, ngày giờ vào, vị trí. Check-in thêm; check-out xóa.
4) Có nút lịch sử đổ xe: plate, thời điểm đổ (in), thời điểm lấy (out), số giờ, tiền phải trả. Thêm khi check-out và thanh toán.
5) “Xóa lỗi”: sau khi upload xong, nhận diện phải chạy ngay; không để user phải gõ ký tự “bất kỳ” thì mới nhận.
6) Thông báo phải có thời gian chi tiết khi check-in/check-out.

## Thông tin đã có (Phase 1)
- Backend đã có:
  - `POST /recognize` trả `plate` từ ảnh.
  - `GET /active` trả danh sách xe đang đỗ.
- DB/service đã có `get_active_vehicles()`.

## Kế hoạch chỉnh sửa tiếp theo
### Phase 2 - UI/UX (chính)
**File `templates/index.html`**
- Viết lại layout:
  - Toggle mode bằng 1 nút (Check-in / Check-out).
  - Khối Plate + Image:
    - `input#plate` (auto-fill và `disabled=true` sau khi recognize)
    - `input#image` (upload ngay)
    - Vùng preview ảnh upload.
  - Nút chính: `btnAction` (Check-in hoặc Check-out theo mode).
  - Vùng thông báo `#result`.
  - Vùng bảng:
    - `#activeTable` cho xe đang đỗ
    - `#historyTable` cho lịch sử

- JS logic:
  - `onchange` của `#image`:
    - gọi `POST /recognize` với file image
    - khi nhận được plate:
      - set `#plate.value`
      - khóa `#plate.disabled=true`
      - hiển thị plate trong thông báo “đã nhận diện” (tuỳ chọn)
      - cập nhật bảng active ngay (gọi `/active`).
  - Nếu user upload ảnh mới:
    - reset state: unlock plate tạm thời rồi set lại sau recognize (tránh bug).

  - Action click:
    - nếu mode=IN: gọi `/check-in` gửi `plate` và `image` (hoặc chỉ plate cũng được; để consistent với yêu cầu check-in có ảnh thì gửi cả image)
    - nếu mode=OUT: gọi `/check-out` gửi `plate` và `image`
    - xử lý thông điệp:
      - nếu status error và message là “Plate already inside” thì thông báo dưới dạng combobox (select) với danh sách entry active cho plate đó.
      - nếu “not found inside” thì thông báo lỗi.
    - cập nhật bảng active + history sau khi thành công.

- “combo box”:
  - Khi check-in trùng biển số đã tồn tại:
    - gọi `/active` để lấy record active của plate đó
    - render `<select>` hiển thị time_in + spot_id, hoặc tối thiểu hiển thị spot_id/time_in.

### Phase 3 - Fix lỗi nhận diện
- Đảm bảo recognize được gọi ngay khi upload file, không liên quan tới việc gõ.
- Đảm bảo không có đoạn code khóa input rồi lại phụ thuộc vào keypress.

### Phase 4 - Test
- Chạy server và test:
  - Upload ảnh -> plate auto fill ngay
  - bấm Check-in -> bảng active tăng, history tăng
  - bấm Check-out -> active giảm, history thêm out_time, duration, fee

## Files cần chỉnh sửa
- `templates/index.html`
- (có thể) `parking/db.py`, `parking/service.py`, `app.py` nếu cần endpoint/format bổ sung (nhưng ưu tiên làm UI trước).

## Outcome
Sau khi làm xong, UI đáp ứng đủ 4 yêu cầu chính và không còn lỗi “phải gõ ký tự mới nhận diện được”.

