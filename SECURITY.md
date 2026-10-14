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

## Public web hardening

- API dùng `Cache-Control: no-store`; HTML dùng `Cache-Control: no-cache`.
- Response public thêm `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin` và `Permissions-Policy` khóa camera/microphone/geolocation.
- HTTPS response thêm HSTS.
- Trang và API đặt `X-Robots-Tag: noindex, nofollow` để tránh index dữ liệu học tập.
- Gemini failure/timeout không làm hỏng phiên chẩn đoán; hệ thống fallback về Evidence Engine.
