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
- Tài khoản giáo viên / quản trị viên bootstrap bằng biến môi trường.
- Lớp học + mã tham gia.
- Dashboard giáo viên.
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
