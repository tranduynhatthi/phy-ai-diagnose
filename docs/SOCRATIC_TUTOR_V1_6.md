# PHY-AI DIAGNOSE — Socratic Tutor v1.6 (nhánh thử nghiệm)

## 1. Kết quả mong đợi

Tính năng gia sư Vật lí 12 hướng đến học sinh còn hổng kiến thức. Khi Evidence Engine đã có **tối thiểu hai bằng chứng và ít nhất một bằng chứng sai** cho một mã lỗi thuộc ontology hiện hành, học sinh có thể khởi động đối thoại gợi mở theo đúng mã lỗi ấy.

**Lưu ý quan trọng:** kết quả của AI gia sư không phải kết luận về lỗi tư duy hay xác nhận sửa lỗi thành công. Gemini không được cập nhật `ErrorProfile`. Hồ sơ lỗi chỉ thay đổi sau phiên **chẩn đoán lại** được xử lý qua Evidence Engine hiện có.

## 2. Kiến trúc và nguồn dữ liệu

- `sgk_physics12.py`: chỉ mục 25 bài Vật lí 12 — Kết nối tri thức, chương, số trang in trên SGK và số trang PDF (PDF = trang in + 1). Tệp SGK được cung cấp là PDF ảnh 126 trang, **chưa có OCR toàn văn được duyệt**. Những câu hỏi gợi mở trong index do dự án biên soạn, không phải trích dẫn nguyên văn.
- `socratic_tutor.py`: bộ điều phối năm giai đoạn, kiểm tra quyền đồng ý, dữ liệu đầu vào, fallback khi Gemini lỗi, giới hạn đầu ra JSON.
- `socratic_tutor_patch.py`: cài ba route vào FastAPI và giao diện đối thoại sau AI Coach ở kết quả chẩn đoán/đề thi.
- Sử dụng bảng `learning_sessions` đã có, `kind=tutor`, `mode=socratic`, lịch sử và audit nằm trong `meta_json`. Không tạo bảng mới hay thay đổi chấm điểm.
- `ErrorProfile` và ontology từ `bank.error_by_id` do Evidence Engine quản lí; chỉ học sinh có hồ sơ lỗi trong tài khoản của mình được sử dụng đúng mã lỗi.
- `tests/test_socratic_tutor.py`: kiểm tra chủ yếu offline, không gọi Gemini.

## 3. Máy trạng thái Socratic

| Bước | Giai đoạn | Mục đích |
|---|---|---|
| 1 | Identify | Nhận diện cách học sinh đang suy nghĩ, yêu cầu dẫn chứng |
| 2 | Contrast | Tạo phản ví dụ, giúp phát hiện mâu thuẫn nhận thức |
| 3 | Reconstruct | Hướng về khái niệm SGK và cho học sinh tự điều chỉnh |
| 4 | Transfer | Chuyển sang ngữ cảnh tương tự không trùng câu cũ |
| 5 | Reflect | Tự giải thích cách kiểm tra lập luận của mình |
| Kết thúc | Recheck | Khởi động bài chẩn đoán khác, không tự sửa hồ sơ lỗi |

Các pha chuyển theo số lượt do server điều khiển; mô hình AI chỉ sinh `feedback` và một `question` cho lượt tiếp theo. Mô hình không quyết định chuyển pha, chấm điểm, hay đặt trạng thái đã sửa lỗi.

## 4. API

- `POST /api/tutor/start`: `{ "error_id": "VLN-01", "llm_consent": false }`. Yêu cầu đăng nhập vai trò student, `SOCRATIC_TUTOR_ENABLED=true`, một hồ sơ có đủ bằng chứng, mã lỗi tồn tại và bài SGK được ghép chắc chắn.
- `GET /api/tutor/{session_id}`: tải lại đúng phiên thuộc về học sinh hiện tại.
- `POST /api/tutor/{session_id}/reply`: `{ "message": "Em nghĩ...", "expected_turn": 0 }`. Server giới hạn 2–700 ký tự, kiểm tra optimistic turn và khóa hàng bằng `with_for_update` để giảm nguy cơ trùng lời đáp.

Trả về các trường: `id`, `status`, `chapter`, `lesson`, `source`, `phase`, `turn`, `max_turns`, `question`, `history`, `consent`, `decision_authority`.

## 5. Sử dụng và cấu hình

### Feature flags — mặc định TẮT

```text
SOCRATIC_TUTOR_ENABLED=false
SOCRATIC_TUTOR_LLM_ENABLED=false
```

Khi cả server và phía học sinh đồng ý, vế tạo câu hỏi cá nhân hóa mới được gọi Gemini. Không chạy thử Gemini hàng loạt khi chưa được người vận hành chấp thuận. Không có AI API key hoặc gặp lỗi sẽ chuyển sang câu hỏi quy tắc, phiên không bị gián đoạn. Tối đa 5 phiên gia sư/học sinh/24 giờ (nếu bản ghi có `created_at`), mỗi phiên tối đa 5 lượt; mỗi lượt tối đa một lời gọi Gemini. Metadata lưu model call counts, token estimate, responseId, không chứa API key.

### Tương tác

Sau khi chẩn đoán xong, bên dưới AI Coach xuất hiện mục **Học cùng AI gia sư** với nút theo mã lỗi. Học sinh xác nhận gửi lập luận tới Gemini hoặc chọn tiếp tục bằng câu hỏi gợi mở có sẵn. Cuối phiên nút **Chẩn đoán lại** mở luồng `/api/practice/start` (mode diagnostic, scope chapter, intensity standard). Selector thích ứng của Evidence Engine sẽ ưu tiên hồ sơ lỗi cần xác nhận lại.

## 6. Ví dụ — Bài 1 Chương I

Nguồn: SGK trang 6–9, PDF trang 7–10; chủ đề *Cấu trúc của chất. Sự chuyển thể*. Nếu `VLN-01` đã được Evidence Engine ghi nhận đủ bằng chứng, câu gợi mở đầu tiên liên hệ chuyển động của các hạt và sự chuyển thể. Học sinh giải thích, AI đặt một câu hỏi phản ví dụ, rồi hỏi cách điều chỉnh suy luận. Sau năm lượt, học sinh bắt buộc làm chẩn đoán lại bằng câu hỏi độc lập. Không suy ra rằng chỉ cần nói đúng trong đối thoại là đã sửa được lỗi.

## 7. Kiểm thử và điều kiện phát hành

Trước khi hợp nhất vào main, cần chạy:
1. `python -m pytest -q tests/test_socratic_tutor.py` trong container đã lắp ráp.
2. Toàn bộ `Dockerfile.releasecheck` (các test hồi quy đã có, kiểm toán 1.000 câu, MathJax và Playwright).
3. E2E với học sinh test: đủ bằng chứng / không đủ bằng chứng / khác người dùng / chấm dứt phiên / bất đồng bộ / giới hạn lượt / đồng ý và không đồng ý Gemini / provider lỗi / chẩn đoán lại.
4. Kiểm toán nội dung hỏi đáp theo ít nhất 4 chương; kiểm tra trang SGK, công thức và cách diễn đạt, đặc biệt không đưa đáp án ngay.
5. Sau khi được phép mới bật model trên môi trường preview, đo lượng gọi API, độ trễ, chi phí và kiểm tra nội dung; sau đó mới cân nhắc production.

**Chưa có kết quả E2E phát hành production của v1.6 ở thời điểm tạo nhánh.** Không thay các yêu cầu kiểm chứng này bằng việc chỉ thấy một trang web chạy.

## 8. Hạn chế biết trước

- Chỉ mục 25 bài là metadata từ PDF ảnh, chưa phải kho học liệu truy hồi full-text. Chưa được quyền khẳng định từng câu gợi mở do AI tạo là nguyên văn nội dung SGK.
- Giai đoạn chuyển pha theo số lượt thay vì đánh giá năng lực ngôn ngữ; cần nghiên cứu hiệu quả giáo dục trước khi mở rộng theo năng lực.
- Lời giải thích trong đối thoại không phải điểm số hoặc nhãn lỗi huấn luyện.
- Với người dùng dưới 18 tuổi, cơ sở giáo dục cần đánh giá yêu cầu thông báo, đồng thuận và lưu giữ dữ liệu phù hợp trước khi bật gửi nội dung tới nhà cung cấp AI.


## 9. Gemini kiểm chứng lập luận — nâng cấp theo yêu cầu người sử dụng

Không được sử dụng chế độ chỉ có câu hỏi quy tắc rồi tuyên bố là AI đã kiểm chứng. Một lượt Gemini thành công trả **bốn trường** theo JSON Schema: `verdict`, `verification_note`, `feedback`, `question`. `verdict` chỉ nhận `consistent` (có căn cứ), `needs_revision` (cần sửa), `insufficient_evidence` (chưa đủ thông tin). AI phải giải thích cụ thể điểm kiểm tra dựa trên `error.repair.concept/contrast/tip` của ontology dự án, không được khẳng định đã trích toàn văn SGK khi thực tế chưa được duyệt OCR. Một lượt phát sinh tối đa một lệnh gọi Gemini, đồng thời tạo nhận xét kiểm chứng tạm thời và câu hỏi tiếp theo.

Nếu không gọi được Gemini, phản hồi giữ `verdict=not_checked` và được ghi rõ **chưa được Gemini kiểm chứng**. Không dùng đánh giá này để thay đổi `ErrorProfile` hoặc chứng nhận khắc phục. Kể cả lượt thứ năm (tự phản tỉnh) cũng yêu cầu kiểm chứng bằng Gemini nếu còn hạn mức; kết thúc luôn phải chuyển qua câu hỏi chẩn đoán mới của Evidence Engine.

Mặc định không có lệnh gọi AI. Khi người quản trị xác nhận key thuộc Gemini **Free Tier**, chính sách dữ liệu của Google phù hợp, và chấp thuận triển khai, cấu hình:

```text
SOCRATIC_TUTOR_ENABLED=true
SOCRATIC_TUTOR_LLM_ENABLED=true
SOCRATIC_TUTOR_DAILY_AI_LIMIT=20
GEMINI_MODEL=gemini-3.1-flash-lite
```

`SOCRATIC_TUTOR_DAILY_AI_LIMIT` đếm số **lần thử gọi** toàn hệ thống trong cửa sổ 24 giờ, kể cả khi nhà cung cấp trả lỗi. PostgreSQL sử dụng khóa advisory cấp giao dịch để tránh vượt giới hạn khi nhiều học sinh gửi cùng lúc; `0` đồng nghĩa khóa toàn bộ Gemini. Dù có hạn mức nội bộ, cấu hình này **không tự đảm bảo tài khoản Gemini nằm ở Free Tier**: quản trị viên phải kiểm tra chính xác bậc và khả năng tính phí trong AI Studio. Google có thể dùng dữ liệu gửi qua Free Tier để cải thiện sản phẩm; khi triển khai với học sinh thật cần thiết lập chính sách dữ liệu, thông báo và sự đồng ý phù hợp. Kiểm thử tự động dùng mock Gemini, không gọi API có thể bị tính phí.
