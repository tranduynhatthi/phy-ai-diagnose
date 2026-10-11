# Security checklist

- Password được băm bằng Argon2; server không lưu plaintext password.
- JWT dùng `SECRET_KEY` từ environment.
- Student không thể tự tạo tài khoản teacher/admin.
- Teacher chỉ xem lớp do mình quản lý; admin có quyền toàn hệ thống.
- Frontend và API được phục vụ cùng origin; production không cần bật CORS nếu không có frontend khác.
- Không public PostgreSQL trực tiếp ra Internet.
- HTTPS do Railway/Render/reverse proxy cung cấp.
- Không commit `.env`.
- Rotate `SECRET_KEY` nếu bị lộ; thao tác này sẽ làm token cũ mất hiệu lực.
- Backup PostgreSQL định kỳ.
- Khi dùng AI model, chỉ deploy model đã được đánh giá độc lập.
