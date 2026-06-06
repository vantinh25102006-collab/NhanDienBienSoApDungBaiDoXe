# TODO - Parking UI & CRUD + Spot toggle

- [ ] 1. Cập nhật `templates/index.html`:
  - [x] 1.1 Thêm panel “đẩy 30%/overlay” khi click ô đỏ, có nút “-” để quay lại.
  - [x] 1.2 Khi đang expanded và click ô đỏ khác: cập nhật nội dung panel theo ô mới.
  - [x] 1.3 Thêm modal sửa biển số UI.
  - [ ] 1.4 Thêm nút/UX Sửa-Xóa cho 2 bảng bằng click dòng + bấm nút trong giao diện chi tiết.
  - [ ] 1.5 Viết JS gọi API: sửa/xóa + refresh tables + refresh spots.


- [ ] 2. Cập nhật backend `parking/db.py` và `parking/service.py`:
  - [x] 2.1 Thêm update/delete cho active/history.
  - [x] 2.2 Khi xóa record liên quan xe đang đổ (history status='IN' hoặc active): xóa active để spot chuyển xanh.


- [ ] 3. Cập nhật `app.py`:
  - [x] 3.1 Thêm endpoints update/delete cho active và history.

- [ ] 4. Test nhanh:
  - [ ] 4.1 Spots: click ô đỏ khác khi expanded → panel đổi thông tin.
  - [ ] 4.2 Active bảng: click dòng → sửa/xóa hoạt động đúng.
  - [ ] 4.3 History bảng: sửa/xóa hoạt động đúng; xóa history đang đổ → active/spot chuyển xanh.


