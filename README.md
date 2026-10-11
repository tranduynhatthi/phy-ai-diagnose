# PHY-AI DIAGNOSE — Production Server

Bản triển khai server của PHY-AI DIAGNOSE cho Vật lí 12.

## Tính năng đã hoàn thiện

- 1.000 câu, 250 câu/chương.
- Ôn tập theo bài / theo chương.
- Chẩn đoán lỗi tư duy bằng Evidence Engine.
- Hồ sơ lỗi cá nhân.
- Phiên sửa lỗi 10 câu.
- Đề luyện cuối năm 18 MCQ + 4 Đúng/Sai + 6 trả lời ngắn, 50 phút.
- Đề thích ứng theo kết quả học gần nhất và chương yếu.
- Tài khoản học sinh.
- Hai khu đăng nhập riêng dành cho giáo viên và học sinh; đăng kí học sinh bằng mã lớp.
- Tài khoản giáo viên / quản trị viên bootstrap bằng biến môi trường.
- Lớp học + mã tham gia.
- Dashboard giáo viên.
- Quản lí học sinh lớp giáo viên phụ trách; giữ tổng quan trường để phối hợp theo dõi.
- Xuất CSV lớp và nhãn giáo viên cho nghiên cứu.
- PostgreSQL production; SQLite dùng được cho chạy thử.
- JWT authentication + Argon2 password hashing.
- Docker / Railway / Render / VPS ready.
- AI model registry tùy chọn; AI không tự ghi đè hồ sơ lỗi.

## Chạy nhanh bằng Docker Compose

```bash
docker compose up --build
```

Mở `http://localhost:8000`.

Tài khoản giáo viên mặc định trong `docker-compose.yml` chỉ dành cho chạy thử. Không dùng mật khẩu đó khi public.

## Chạy trực tiếp

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# sửa SECRET_KEY, DATABASE_URL và tài khoản giáo viên
uvicorn app.main:app --reload --port 8000
```

API docs: `/docs`.

## Kiểm tra trước deploy

```bash
python scripts/validate_bank.py
pytest -q
```

Ngân hàng phải trả về 1.000 câu và 250 câu cho từng chương.

Mã ứng dụng trong repository được đóng gói ở `deploy_bundle`; Dockerfile giải nén và áp dụng các patch trước khi cài phụ thuộc. Khi kiểm tra bản giải nén bằng Python, đặt `PHY_APP_ROOT` thành thư mục chứa `app/` và chạy riêng từng nhóm để các cấu hình cơ sở dữ liệu thử nghiệm không ảnh hưởng nhau:

```bash
PHY_APP_ROOT=/path/to/generated-app python -m pytest -q tests/test_homepage_cleanup.py tests/test_role_access.py
PHY_APP_ROOT=/path/to/generated-app PHY_PYTHON=/path/to/venv/bin/python node tests/test_role_portals.cjs
PHY_APP_ROOT=/path/to/generated-app PHY_PYTHON=/path/to/venv/bin/python node tests/test_admin_accounts.cjs
```

Kiểm tra trình duyệt dùng Playwright/Chromium và cơ sở dữ liệu tạm riêng. Các luồng gồm hai cổng đăng nhập, giao diện điện thoại, tạo trường/lớp, tham gia lớp, báo cáo học sinh, đổi mật khẩu và phục hồi phiên hết hạn. Patch dọn trang chủ chỉ xóa các phần giới thiệu, giữ nguyên biểu mẫu đăng nhập.

Trang quản trị đặt lại bộ lọc khi đăng nhập để hiển thị danh sách tài khoản đã đăng kí. Nếu tìm kiếm không có kết quả, chọn **Xóa bộ lọc** cạnh danh sách để xem tất cả; lỗi tải danh sách có nút thử lại. Khi đăng xuất, danh sách và các ô mật khẩu admin được xóa khỏi giao diện.

## AI

Bản public hoạt động hoàn chỉnh bằng Evidence Engine + adaptive engine ngay cả khi chưa có ML model đã huấn luyện.

- Không có model: `/api/ai/status` trả `RULE_ENGINE_AI_READY`.
- Có model đã kiểm định: chép các file `.pkl` và `registry.json` vào `models/`, cài `requirements-ai.txt`, rồi dùng `Dockerfile.ai`.

Không nên đưa model vào production nếu chưa đánh giá trên học sinh độc lập với tập train.

## Dữ liệu

Question bank là dữ liệu chỉ đọc trong `app/data/question_bank.json`.

Dữ liệu người dùng được lưu trong PostgreSQL:
- users
- classrooms
- enrollments
- learning_sessions
- responses
- error_profiles
- teacher_labels

Không dùng họ tên học sinh trực tiếp trong file training export; script xuất training data băm student ID.
