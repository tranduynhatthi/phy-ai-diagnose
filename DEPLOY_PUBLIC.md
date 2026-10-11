# PUBLIC PHY-AI DIAGNOSE LÊN SERVER

## Phương án khuyến nghị: Railway + PostgreSQL

### 1. Đưa thư mục này lên GitHub

Repository root phải chứa:

- `Dockerfile`
- `requirements.txt`
- `railway.toml`
- thư mục `app/`

Không commit file `.env`.

### 2. Tạo PostgreSQL trên Railway

Trong Railway Project, thêm PostgreSQL. Railway cung cấp biến `DATABASE_URL` cho dịch vụ database.

### 3. Tạo Web Service từ GitHub repository

Railway phát hiện `Dockerfile`. Gán các biến môi trường cho service web:

```text
ENVIRONMENT=production
DATABASE_URL=<reference tới DATABASE_URL của Postgres>
SECRET_KEY=<chuỗi ngẫu nhiên dài>
TEACHER_USERNAME=<tên đăng nhập giáo viên đầu tiên>
TEACHER_PASSWORD=<mật khẩu mạnh>
TEACHER_NAME=<họ tên giáo viên>
ADMIN_USERNAME=<tùy chọn>
ADMIN_PASSWORD=<tùy chọn>
ALLOW_STUDENT_REGISTRATION=true
```

Tạo secret bằng:

```bash
python scripts/generate_secret.py
```

### 4. Public domain

Sau khi deploy thành công, vào Networking và tạo public domain. Kiểm tra:

- `/api/health`
- `/docs`
- trang `/`

### 5. Sau khi xác nhận tài khoản giáo viên hoạt động

Có thể xóa `TEACHER_PASSWORD` khỏi environment rồi redeploy. Tài khoản đã được lưu trong database.

---

## Render

1. Tạo PostgreSQL database trên Render.
2. Tạo Web Service từ GitHub repository.
3. Chọn Docker runtime.
4. Gán `DATABASE_URL` và các biến giống phần Railway.
5. Health check path: `/api/health`.
6. Render sẽ build từ `Dockerfile`.

---

## VPS Ubuntu + Docker

### 1. Cài Docker + Docker Compose

### 2. Copy repository lên server

### 3. Sửa biến môi trường

Nên dùng file `.env` riêng và không commit Git.

### 4. Chạy

```bash
docker compose up -d --build
```

### 5. HTTPS

Đặt ứng dụng sau Caddy/Nginx/Traefik và bật HTTPS. Không public port PostgreSQL ra Internet.

---

# CHECKLIST TRƯỚC KHI GO-LIVE

- [ ] `SECRET_KEY` đã đổi và đủ dài.
- [ ] Mật khẩu teacher/admin không còn giá trị demo.
- [ ] `ENVIRONMENT=production`.
- [ ] Dùng PostgreSQL, không dùng SQLite cho production nhiều người dùng.
- [ ] HTTPS hoạt động.
- [ ] `/api/health` trả `total=1000`, mỗi chương = 250.
- [ ] Đăng ký học sinh thử thành công.
- [ ] Giáo viên tạo lớp và học sinh tham gia bằng mã lớp thành công.
- [ ] Ôn tập, chẩn đoán, sửa lỗi, luyện đề đều chạy được.
- [ ] Dashboard và xuất CSV chạy được.
- [ ] Có chính sách sao lưu database.
- [ ] Không đưa `.env`, mật khẩu hoặc database dump lên GitHub.
- [ ] Đã thông báo mục đích lưu dữ liệu học tập cho học sinh.
- [ ] Nếu dùng dữ liệu học sinh để train AI, phải tách train/test theo học sinh và có quy trình đồng thuận phù hợp.
