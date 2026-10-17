# PHY-AI DIAGNOSE – Quản trị ngân hàng câu hỏi v1

## Phạm vi và trạng thái an toàn

- Phát triển trên nhánh `feature/question-bank-admin-v1`. Chưa tự hợp nhất vào `main`, không thay đổi Railway/PostgreSQL thật.
- Ngân hàng nền tảng **1.000 câu/68 mã lỗi** tiếp tục nằm trong bộ mã có kiểm chứng checksum và audit hiện tại.
- `QUESTION_ADMIN_ENABLED=false` (mặc định) → API quản trị mới trả 503 với tài khoản quản trị; giáo viên/học sinh không được truy cập.
- `QUESTION_BANK_PUBLISH_ENABLED=false` (mặc định) → các câu đã duyệt trong bảng PostgreSQL **chưa xuất hiện trong phiên học**.
- Chỉ sau kiểm thử hồi quy và đánh giá sư phạm mới được bật cờ thứ hai.

## Cơ sở dữ liệu và workflow

Bảng riêng `managed_question_v1` (PostgreSQL hoặc SQLite riêng trong test); không sửa, không xóa bảng kết quả học tập. Khi quản trị viên mở tính năng lần đầu, bảng được tạo bằng SQLAlchemy `checkfirst`.

| Thao tác | Điều kiện | Kết quả |
|---|---|---|
| Thêm | Admin | `draft`, không công khai |
| Sửa | Admin + `expected_revision` | `draft`, tăng revision, giữ bản công bố trước |
| Gửi duyệt | `draft` | `submitted` |
| Duyệt | `submitted` | Lưu bản công bố bất biến `QMG-...-vN` |
| Đề nghị xóa/ẩn | Bản đang có | `archive_requested`, chưa thay kết quả học |
| Duyệt xóa/ẩn | `archive_requested` | `archived` (xóa mềm), vẫn giữ dữ liệu phiên cũ |

Quản trị viên có thể tự duyệt để hỗ trợ trường chỉ có một admin; lịch sử chứa `editor_id`, `approver_id`, `history_json` và thời gian. Đây **chưa phải quy trình hai người kiểm duyệt độc lập**. Nếu dùng thực tế với nhiều nhân sự, nên bật mô hình biên tập viên và người duyệt riêng.

`source_id` trỏ mã câu trong ngân hàng chuẩn, chỉ một bản quản trị cho mỗi mã gốc. Khi bản sửa được duyệt, câu gốc được thay trong **pool của phiên luyện tập/chẩn đoán mới**, nhưng mã cũ không bị xóa khỏi từ điển chấm điểm, tránh thay đáp án giữa chừng đối với học sinh đang làm bài. Phiên mới được tham chiếu mã phiên bản `...-vN` bất biến. Dữ liệu đã duyệt được đồng bộ khi tạo pool, cả khi hệ thống chạy nhiều worker.

**Phạm vi hiện tại:** overlay kết nối với `bank.pool` cho luyện tập và chẩn đoán. Chưa khẳng định toàn bộ logic chọn câu **đề ôn tập cuối năm** lấy từ overlay; đề cần E2E riêng trước khi công bố hỗ trợ. Chưa chuyển 1.000 câu chuẩn vào DB; chúng vẫn được xem/biên tập thông qua bản dự thảo và nằm trong gói chuẩn bảo vệ nguyên trạng.

## Excel (.xlsx)

Đăng nhập Admin → **Quản trị ngân hàng câu hỏi** → **Tải mẫu Excel**. Mẫu gồm **một sheet, 14 cột theo đúng thứ tự**:

`source_id | chapter | lesson | type | prompt | context | options | statements | answer | explain | error | diagnostic | tolerance | unit`

Quy tắc:
- `source_id`: bỏ trống để thêm câu mới; điền mã câu gốc nếu muốn sửa một câu trong 1.000 câu.
- `chapter`: `Chương I` … `Chương IV`; `lesson`: `Bài 1` … `Bài 25` nhưng phải nằm trong đúng chương.
- `type`: `mcq`, `tf`, `short`.
- `prompt`: nội dung câu; `explain`: lời giải bắt buộc.
- `options` với `mcq`: đúng 4 đáp án phân cách bằng `|`, ví dụ `A lựa chọn|B lựa chọn|C lựa chọn|D lựa chọn`. `answer`: chữ `A`/`B`/`C`/`D` (khuyến nghị); hệ thống lưu chỉ số 0–3.
- `statements` với `tf`: JSON array 4 phần tử, mỗi phần tử có `text`, `answer` (true/false), `explain`.
- `short`: `answer` số, `tolerance` dương hữu hạn, `unit` nếu có.
- `error`: mã lỗi tư duy có thực, đúng chương/bài. Khi `diagnostic=true` phải có `error`.
- Tối đa **300 câu/lần**, **3 MB**, một sheet, không công thức và không dòng ẩn. Nếu sai ở một dòng, **không nhập bất kỳ câu nào của file**.
- Import tạo **draft**; cần gửi duyệt và phê duyệt mới có bản công bố.

**Kiểm duyệt chuyên môn bắt buộc**: Đáp án đúng, phương án nhiễu, công thức, đơn vị, câu chữ, mức độ nhận thức, ngữ cảnh SGK, mã lỗi cùng bằng chứng chẩn đoán. Kiểm tra cấu trúc tự động không thay được đánh giá sư phạm.

## API quản trị (đều cần JWT role=admin)

- `GET /api/admin/question-bank/status`
- `GET /api/admin/question-bank/ontology`
- `GET /api/admin/question-bank?page=1&limit=30&status=draft&chapter=Chương%20I`
- `GET /api/admin/question-bank/{id}`
- `POST /api/admin/question-bank` body `{"source_id":null,"question":{...}}`
- `PUT /api/admin/question-bank/{id}` body `{"expected_revision":N,"question":{...}}`
- `POST /api/admin/question-bank/{id}/submit` và `/approve`
- `POST /api/admin/question-bank/{id}/archive-request`
- `GET /api/admin/question-bank/template.xlsx`
- `POST /api/admin/question-bank/import-xlsx` raw bytes XLSX, MIME `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

Không có API xóa cứng dữ liệu học sinh/câu hỏi đã công bố. Câu được lưu trữ khỏi pool mới không xóa lịch sử chứng cứ trong phiên cũ.

## Trình tự triển khai đề xuất

1. CI trên nhánh riêng với `Dockerfile.releasecheck` và SQLite tạm: test quyền admin, 3 loại đáp án, import và trạng thái workflow, chấm điểm, bản cũ.
2. Tạo **bản sao Postgres trên môi trường thử nghiệm** nếu có tài nguyên; không chạy sửa dữ liệu ngay trên production trong giai đoạn đầu.
3. Hậu kiểm 5 câu Bài 1 Chương I, thử học sinh làm bài từ đầu đến cuối và xác minh Evidence Engine.
4. Sao lưu Postgres thật trước phát hành và bật `QUESTION_ADMIN_ENABLED=true` trước, giữ `QUESTION_BANK_PUBLISH_ENABLED=false` ít nhất một vòng kiểm duyệt.
5. Chỉ bật publish flag sau khi rà soát E2E chọn câu/chấm câu trên ứng dụng thật; đổi cờ yêu cầu khởi động lại container.
6. Rollback nhanh: `QUESTION_BANK_PUBLISH_ENABLED=false` rồi deploy lại hoặc khởi động lại dịch vụ → quay về 1.000 câu nền tảng; bản quản trị DB vẫn được giữ an toàn.
