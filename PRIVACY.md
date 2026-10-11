# Privacy / dữ liệu học sinh

Ứng dụng chỉ cần:
- tên đăng nhập;
- họ tên hiển thị;
- lớp học;
- câu trả lời và kết quả học tập.

Không yêu cầu email, số điện thoại hoặc thông tin định danh khác.

Khuyến nghị khi triển khai với học sinh:
- dùng username mã hóa theo lớp thay vì thông tin định danh nhạy cảm;
- thông báo rõ mục đích lưu kết quả học tập;
- chỉ giáo viên phụ trách lớp được xem dashboard;
- database training/export dùng student ID băm;
- quy định thời gian lưu và xóa dữ liệu;
- học sinh có endpoint xóa tài khoản của chính mình (`DELETE /api/me`).
