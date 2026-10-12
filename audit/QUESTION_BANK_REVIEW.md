# Rà soát nội dung và hiển thị Vật lí 12

Phiên bản: `2026.10-1000q-quality-v4-content-render-audit`.

Đã đọc 1.000 câu ở bốn chương (250 câu/chương), gồm 532 câu trắc nghiệm, 218 câu Đúng/Sai với 872 mệnh đề và 250 câu trả lời ngắn. Đã tính lại toàn bộ 250 câu trả lời ngắn, thực hiện 668 phép kiểm tra định lượng trên 619 câu. Các nhãn đã kiểm chứng của bản cũ không được dùng làm bằng chứng thay cho việc đọc và tính lại.

Bản sửa thay đổi 111 câu: gồm khóa đáp án, làm tròn, dung sai chấm, điều kiện hình học, giả thiết, đơn vị, ký hiệu, câu dẫn và lời giải. Toàn bộ thay đổi trước/sau và lý do nằm trong `../question_bank_audit.json`; các công thức, dữ kiện và kết quả tính độc lập nằm trong `question-bank-review.json`.

| Câu | Vấn đề cũ | Sửa |
| --- | --- | --- |
| SRC-I7-01 | Chọn 5 giai đoạn trong khi lời giải liệt kê 4 | Chọn phương án 4 giai đoạn |
| EXT-07-S01 | 95,55 kJ làm tròn thành 95,5 | 95,6 kJ |
| EXT-12-S01 | 5,175 làm tròn thành 5,17 | 5,18 |
| NEW-22-S05 | 9,315 MeV làm tròn thành 9,31 | 9,32 MeV |
| NEW-16-M01 | Hai phương án cùng bằng từ thông 0 | Giữ duy nhất phương án 0 |
| SRC-III16-06 | Chưa đủ điều kiện hình học để dùng Blv | Nêu ba phương đôi một vuông góc |
| SRC-III19-02 | Điện trường biến thiên luôn tạo B biến thiên | Nêu đúng quan hệ Maxwell–Ampère |
| SRC-IV24-09 | Thiếu ngoặc mẫu số 1/3,204×10^-11 | 1/(3,204×10^-11) |

Đã làm rõ các hằng số và gần đúng được dùng: đổi Celsius theo mô hình phổ thông khi cần, khối lượng riêng nước để đổi lít sang kg, khối lượng mol U-235 và đổi eV sang J. Những phép chấm chỉ nhận một giá trị số hợp lệ (dấu phẩy hoặc chấm, số mũ e); không còn lấy số đầu từ một chuỗi có nhiều đáp án, biểu thức sai hoặc dữ liệu không phải số. Dấu âm Unicode được giữ đúng. Dung sai không nhận giá trị làm tròn sai ở chữ số liền kề.

Một bộ định dạng văn bản/LaTeX thống nhất thay hai bộ bọc nối tiếp, giữ dấu âm, chỉ số, số mũ, phân số, đơn vị và ký hiệu hạt nhân. MathJax dùng phiên bản cố định 3.2.2. Đã kiểm tra dữ liệu hiệu lực và các đường hiển thị câu hỏi, trắc nghiệm, Đúng/Sai, trả lời ngắn, sửa lỗi, phản hồi và ôn lại đề.

Kiểm tra lại bản giải nén bằng `scripts/validate_audited_bank.py`, `tests/test_question_content_audit.py` và `tests/test_math_rendering.cjs` theo hướng dẫn README. Bộ kiểm tra ngăn áp dụng sửa đổi lên một phiên bản ngân hàng chưa được rà soát, kiểm tra câu trả lời làm tròn bằng Decimal và dùng MathJax thực để tìm lỗi hiển thị.

Phạm vi bằng chứng: rà soát vật lí/nội dung nội bộ và tính lại từ dữ kiện của câu. Các tệp SGK/PDF/Word được ghi ở metadata không được cung cấp để đối chiếu nguyên bản, số trang hoặc nguồn trích dẫn. Các bài toán vẫn dùng những mô hình và gần đúng đã nêu, không coi hằng số gần đúng là giá trị đo tuyệt đối.
