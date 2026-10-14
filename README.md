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

## Kiểm tra nội dung và LaTeX

Ngân hàng hiệu lực gồm bản V3 và các sửa đổi đã rà soát trong `question_bank_audit.json`. [Báo cáo rà soát](audit/QUESTION_BANK_REVIEW.md) ghi phạm vi 1.000 câu, 872 mệnh đề Đúng/Sai và 668 phép tính độc lập; [sổ tính kiểm tra](audit/question-bank-review.json) lưu dữ kiện và kết quả. Không dùng riêng JSON gốc trong bundle để kết luận bản hiệu lực đã được kiểm tra.

```bash
PHY_APP_ROOT=/path/to/generated-app python scripts/validate_audited_bank.py --export /tmp/phy-reviewed-bank.json
PHY_APP_ROOT=/path/to/generated-app python -m pytest -q tests/test_question_content_audit.py
npm install --prefix /tmp/phy-math-tests mathjax-full@3.2.2
PHY_APP_ROOT=/path/to/generated-app PHY_BANK_JSON=/tmp/phy-reviewed-bank.json PHY_MATHJAX_ROOT=/tmp/phy-math-tests/node_modules/mathjax-full PHY_MATH_AUDIT_DIR=/tmp/phy-math-results node tests/test_math_rendering.cjs
```

Bộ kiểm tra trình duyệt cần Playwright và Chromium (đã có trong môi trường cloud). Nó dùng MathJax 3.2.2 thực để kiểm tra toàn bộ câu dẫn, lựa chọn, mệnh đề, lời giải, đơn vị và nội dung sửa lỗi ở tám đường hiển thị. Bộ xử lí LaTeX thống nhất giữ công thức đã có, không dùng mã giữ chỗ và không bọc công thức lồng nhau. Kiểm tra chấm bài dùng Decimal ở các điểm làm tròn giữa, từ chối chuỗi nhiều đáp án, giữ dấu âm và kiểm tra dung sai theo yêu cầu câu hỏi.

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


## Hybrid AI v1.2 — Gemini + Evidence Engine

Bản production dùng Gemini API để phân tích phần giải thích của học sinh nhưng không thay Evidence Engine. Trong phiên Chẩn đoán, học sinh có thể nhập 1–3 câu giải thích cách nghĩ; backend gửi phần lập luận cùng ngữ cảnh câu hỏi tới Gemini và chỉ nhận candidate evidence theo ontology lỗi hợp lệ.

- Gemini không tự gán trạng thái lỗi và không thể một mình tạo hồ sơ lỗi.
- Evidence Engine vẫn là lớp quyết định chính; tín hiệu Gemini chỉ hỗ trợ khi đã có bằng chứng sai định lượng.
- Production hiện dùng `GEMINI_MODEL=gemini-3.1-flash-lite`.
- Mỗi response thành công lưu `responseId` của Gemini làm `request_id` phục vụ kiểm tra/audit.
- Thiếu API key, timeout hoặc provider lỗi thì hệ thống fallback về Evidence Engine và phiên chẩn đoán vẫn tiếp tục.
- Sau can thiệp, một phiên chẩn đoán lại có ít nhất hai probe đúng cho cùng lỗi sẽ giảm độ tin cậy hồ sơ lỗi, nhưng vẫn giữ lịch sử bằng chứng và trạng thái sửa lỗi.
- Kiểm tra trạng thái tại `GET /api/ai/status`; smoke test dành cho giáo viên/admin tại `POST /api/ai/analyze-reasoning`.
- Regression E2E cho luồng VLN-01 nằm tại `scripts/e2e_vln01_core.py`.

Để kích hoạt, đặt `AI_PROVIDER=gemini`, `GEMINI_API_KEY` và `GEMINI_MODEL=gemini-3.1-flash-lite` trong Railway Variables.
