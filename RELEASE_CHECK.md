# Release check — 2026-10-14

Bản release candidate `release-hardening-v1-3` đã được lắp ráp bằng đúng chuỗi patch của Dockerfile production và chạy qua release gate độc lập trên Railway.

## Kết quả release gate

- Python regressions: **77 passed**, 1 deprecation warning của Starlette/AnyIO; không có test lỗi.
  - dọn trang chủ và giữ nguyên khu đăng nhập;
  - phân quyền giáo viên/học sinh/admin và phạm vi lớp;
  - hậu kiểm nội dung, chấm số và làm tròn;
  - adaptive diagnostic selector;
  - privacy notice và security headers.
- Playwright/Chromium — cổng giáo viên/học sinh: **PASS toàn bộ**.
  - phục hồi khi metadata lỗi;
  - hai cổng đăng nhập riêng và chặn đăng nhập sai cổng;
  - responsive layout;
  - đăng kí học sinh, tham gia lớp;
  - dashboard cá nhân/trường;
  - roster, báo cáo học sinh, đổi mật khẩu;
  - cô lập quyền admin.
- Playwright/Chromium — quản trị tài khoản: **PASS toàn bộ**.
  - hiển thị danh sách;
  - reset bộ lọc khi đăng nhập lại;
  - khôi phục danh sách rỗng;
  - retry khi API lỗi;
  - xóa trạng thái admin khi đăng xuất.
- Ngân hàng hiệu lực:
  - **1.000 câu**;
  - Chương I–IV: **250 câu/chương**;
  - 872 mệnh đề Đúng/Sai;
  - 250 đáp án trả lời ngắn được tái tính;
  - 668 kiểm tra số độc lập;
  - `issues = []`.
- MathJax/rendering:
  - 7.034 trường được typeset;
  - 8.190 biểu thức;
  - 8 đường hiển thị (practice, feedback, repair, true/false, short-answer unit, exam, exam review);
  - `errors = []`;
  - `status = passed`.
- Release-check container khởi động Uvicorn thành công sau khi hoàn tất toàn bộ test.

## Chẩn đoán thích ứng

Selector cũ chọn ngẫu nhiên đã được giữ cho chế độ luyện tập, nhưng chế độ **Chẩn đoán** dùng chiến lược riêng:

- học sinh chưa có hồ sơ lỗi: `coverage_first` để phủ các mã lỗi có bằng chứng trong bài/chương;
- học sinh đã có hồ sơ lỗi: `profile_targeted`, ưu tiên lỗi đã sửa và lỗi có độ tin cậy cao;
- khi ngân hàng có đủ dữ liệu, một lỗi mục tiêu nhận ít nhất hai probe độc lập trong cùng phiên;
- session metadata lưu `diagnostic_strategy` và `diagnostic_target_errors`;
- chẩn đoán lại sau sửa lỗi không còn phụ thuộc việc lấy ngẫu nhiên đúng câu xác nhận.

## Public release hardening

- API trả `Cache-Control: no-store`.
- HTML trả `Cache-Control: no-cache`.
- Bổ sung `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `X-Robots-Tag`.
- Bật HSTS khi request đi qua HTTPS.
- Cổng học sinh hiển thị thông báo quyền riêng tư và giải thích rõ phần dữ liệu được gửi tới AI.
- Gemini vẫn chỉ tạo candidate evidence; Evidence Engine giữ quyền quyết định hồ sơ lỗi.

## Kiểm tra production trước release candidate

Ở production hiện tại trước khi merge release-hardening:
- health, đăng nhập giáo viên/học sinh, đăng kí học sinh, JWT và phân quyền đã smoke-test trực tiếp;
- Gemini API thật đã trả candidate `VLN-01` có request ID;
- luồng `RULE_LLM -> hồ sơ lỗi -> sửa lỗi 10/10 -> chẩn đoán lại` đã được xác minh;
- không ghi nhận HTTP 5xx trong cửa sổ 24 giờ được kiểm tra.

## E2E production sau merge

Đã chạy trực tiếp trên production và **PASS**:

- phiên chẩn đoán tạo ngay trong **một lần start**, không còn vòng lặp lấy ngẫu nhiên;
- phiên đầu chứa hai probe VLN-01 có cấu trúc: `EXT-01-C01` và `EXT-01-T01`;
- Gemini thật trả `used=true`, model `gemini-3.1-flash-lite`, có request ID và candidate `VLN-01` cho cả hai probe;
- Evidence Engine hợp nhất thành `decision_source=RULE_LLM`, confidence VLN-01 = **55.0**;
- phiên sửa lỗi đạt **10/10**, trạng thái `Đã sửa tốt`;
- phiên chẩn đoán lại chọn `profile_targeted` ngay lần đầu và chứa ba probe VLN-01;
- sau khi trả lời đúng toàn bộ recheck, confidence giảm **55.0 → 27.5**, `evidence_total 5 → 8`, lịch sử `Đã sửa tốt` được giữ;
- smoke script khôi phục dữ liệu test về trạng thái ban đầu (`CLEANUP restored=true`);
- deployment production hoàn tất `SUCCESS`.

Pre-deploy E2E command đã được gỡ sau kiểm thử; các deployment tiếp theo không tự chạy smoke test với Gemini.

