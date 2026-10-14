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



# Release candidate v1.4 — Student self-study

## Mục tiêu sản phẩm

- Trọng tâm: tăng khả năng tự học và năng lực Vật lí của học sinh trung bình, yếu.
- Public UI chỉ còn cổng học sinh; giao diện quản lí giáo viên không còn hiển thị.
- Lộ trình hiển thị trực tiếp: Chẩn đoán → Sửa lỗi → Luyện đề → Kiểm tra lại.
- Đề ôn tập dùng mức Tự động theo kết quả gần đây làm lựa chọn mặc định.
- Khung nhập phần giải thích cách nghĩ có chiều cao tối thiểu 160 px và cho phép kéo giãn.

## Chẩn đoán sau đề

Endpoint nộp đề trả thêm post_exam_diagnosis:
- tổng hợp bằng chứng lỗi từ các câu có mapping lỗi hợp lệ;
- trả danh sách lỗi, tiêu đề, bài/chương và confidence;
- xác định chương có tỉ lệ làm đúng thấp nhất;
- UI cung cấp nút Sửa lỗi ngay;
- nếu chưa đủ bằng chứng cho một lỗi cụ thể, học sinh được chuyển sang Chẩn đoán sâu ở chương yếu nhất.

## Kiểm duyệt công thức SGK

Question bank hiệu lực áp dụng student_selfstudy_policy sau content audit. Release gate kiểm tra rằng các công thức đã học trong SGK Vật lí 12 không còn bị chép lại như gợi ý trong câu dẫn. Công thức chỉ được dùng ở lời giải/sửa lỗi sau khi học sinh trả lời.

Kết quả release gate:
- SGK_FORMULA_STEM_VIOLATIONS = 0.
- Python regressions: 81 passed, 1 deprecation warning; không có test lỗi.
- Browser regression student-only: PASS.
- Đăng kí không cần mã lớp, đăng nhập và điều hướng student-only: PASS.
- Khung giải thích chẩn đoán >= 150 px trên browser test: PASS.
- Tạo đề tự động và submit đề: PASS.
- Response sau đề có post_exam_diagnosis và weak_chapter: PASS.
- Audit ngân hàng: 1.000 câu, 250 câu/chương, issues = [].
- MathJax: 7.034 trường, 8.119 biểu thức, 8 đường hiển thị, errors = [], status = passed.
- Release-check container khởi động Uvicorn thành công.


# Release candidate v1.5 — Visible AI Coach

## Vai trò AI được nâng cấp

- Per-question diagnostic: Gemini đọc phần giải thích của học sinh và trả candidate signals hiển thị trực tiếp trên giao diện dưới nhãn **Dấu hiệu cần kiểm chứng**.
- Candidate signals luôn ghi rõ chưa phải kết luận cuối cùng; Evidence Engine giữ quyền cập nhật hồ sơ lỗi.
- Diagnostic finish: Gemini AI Coach tạo giải thích ngắn và kế hoạch tự học 3 bước dựa trên hồ sơ lỗi đã được Evidence Engine kiểm chứng.
- Exam finish: AI Coach tổng hợp lỗi đã kiểm chứng + chương yếu nhất để tạo kế hoạch 15–20 phút sau đề.
- Mọi `focus_errors` từ mô hình được lọc theo mã lỗi có trong verified profiles; mã do mô hình tự tạo bị loại.
- Mỗi AI Coach response lưu audit metadata: provider/model/request_id và `decision_authority=Evidence Engine`.
- Provider error/quota/timeout dùng Evidence Engine fallback và không làm hỏng phiên học.

## Kết quả release gate v1.5

- AI Coach patch: applied successfully.
- Python regressions: **85 passed**, 1 deprecation warning; 0 failed.
- Test riêng kiểm tra AI Coach: fallback có 3 bước, lọc mã lỗi bịa, giữ Evidence Engine authority, UI có thông điệp AI rõ ràng.
- Student-only Playwright: **PASS**.
- SGK formula-stem audit: **0 violations**.
- Question bank audit: 1.000 câu, 250 câu/chương, `issues=[]`.
- MathJax: 7.034 trường, 8.119 biểu thức, 8 render paths, `errors=[]`, `status=passed`.
- Release-check deployment Railway: **SUCCESS**.

Trước khi đánh dấu production v1.5 hoàn tất cần chạy một request Gemini thật trên production để kiểm tra `ai.used=true`, `request_id`, verified `focus_errors`, kế hoạch đúng 3 bước và fallback đã được kiểm thử bằng regression.
