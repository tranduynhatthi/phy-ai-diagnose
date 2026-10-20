# PHY-AI DIAGNOSE — Đánh giá độc lập chất lượng bộ 1.000 câu (V5)

**Ngày đánh giá:** 20/10/2026  
**Cơ sở:** ngân hàng gốc trong `deploy_bundle`, gói hiệu chỉnh V3 (619 mục), danh sách 111 câu hiệu chỉnh V4, và SGK Vật lí 12 — Kết nối tri thức do người dùng cung cấp.  
**Nguyên tắc:** tách **kiểm tra cấu trúc**, **xác minh khoa học**, **đánh giá khả năng chẩn đoán**, **đo lường trên học sinh thực tế**. Kết quả của lớp trước **không tự động** chứng minh lớp sau.

## A. Số liệu kiểm chứng

| Chỉ tiêu | Kết quả |
|---|---:|
| Tổng câu / mã câu duy nhất | 1.000 / 1.000 |
| Phân bố Chương I/II/III/IV | 250 / 250 / 250 / 250 |
| Trắc nghiệm 4 lựa chọn | 532 |
| Câu Đúng/Sai (4 mệnh đề) | 218 (872 mệnh đề) |
| Câu trả lời ngắn | 250 |
| Câu gắn nhãn chẩn đoán | 599 |
| Câu không gắn nhãn chẩn đoán | 401 |
| Số mã lỗi trong câu hỏi | 67 |
| Mức nhận biết NB | 75 (7,5%) |
| Mức thông hiểu TH | 286 (28,6%) |
| Mức vận dụng VD | 565 (56,5%) |
| Mức vận dụng cao VDC | 74 (7,4%) |
| Đáp án MCQ vị trí A/B/C/D | 133 / 133 / 134 / 132 |
| Câu Đ/S có mẫu ĐĐSS | 113/218 (51,83%) |
| Câu Đ/S có mẫu ĐSĐS | 49/218 (22,48%) |
| Tổng hai mẫu phổ biến trên | 162/218 (74,31%) |
| Số câu Đ/S được lập kế hoạch đảo thứ tự mệnh đề | **102** |
| Sau đảo: ĐĐSS / ĐSĐS | **33 / 33** |
| Mức xuất hiện lớn nhất của một mẫu Đ/S sau đảo | **33** |
| Trùng câu dẫn hoàn toàn trong cùng bài (chuẩn hóa khoảng trắng/dấu câu) | 0 |
| Trùng chính xác phương án MCQ sau chuẩn hóa thận trọng | 0 |

**Lưu ý:** Kiểm tra trùng phương án không được xóa dấu cộng/trừ hoặc kí hiệu toán học vì làm vậy sẽ báo nhầm các đáp án như `-10 J` và `+10 J`. Không phát hiện trùng tuyệt đối **không chứng minh** đã loại trùng về ý tưởng hoặc chỉ thay dữ kiện số.

## B. Kết luận chuyên môn

### B1. Điểm đã đạt

1. Đủ 1.000 câu với 4 chương và 3 dạng câu hỏi, mã câu không trùng.
2. Vị trí đúng A/B/C/D của câu trắc nghiệm đã cân bằng (133/133/134/132), không cần sửa.
3. V4 từng tính lại 250 đáp án ngắn và thực hiện 668 phép kiểm tra định lượng trên 619 câu; sửa 111 câu do dữ kiện, dấu, đơn vị, làm tròn, phương án tương đương và các lỗi diễn đạt. Đây là **bằng chứng hậu kiểm nội bộ**, chưa phải xác thực thực nghiệm.
4. Không phát hiện câu dẫn trùng hoàn toàn trong cùng bài ở bản hiệu lực được đọc.

### B2. Nhược điểm và hướng xử lí

| Ưu tiên | Nhược điểm | Biện pháp | Trạng thái |
|---|---|---|---|
| P0 | 74,31% câu Đ/S theo hai mẫu lặp | Hoán đổi **102 bộ thứ tự mệnh đề**; giữ nguyên từng mệnh đề, truth key, giải thích, mã lỗi | **Đã chuẩn bị bản V5 trên nhánh đánh giá** |
| P0 | Câu Đ/S chỉ có hai hoặc ba phát biểu đúng (196 câu 2Đ–2S; 22 câu 3Đ–1S) | Biên soạn mới/mở rộng các mệnh đề thật sự sai để có 1Đ–3S, 0Đ–4S, 4Đ–0S khi phù hợp; giáo viên phải đọc duyệt từng trường hợp | **Chưa hoàn tất** |
| P0 | Mã lỗi TT-13, HN-13, HN-14 mới có 1 câu trong ngân hàng | Soạn thêm probe độc lập và kiểm tra mã lỗi tương ứng; không kết luận khi chỉ có 1 bằng chứng | **Chưa hoàn tất** |
| P0 | Một mã lỗi gắn chung cho câu MCQ chưa cho biết lý do của mỗi lựa chọn sai | Bổ sung ánh xạ **lựa chọn sai → giả thuyết lỗi cụ thể**, chỉ dùng để gợi ý, xác nhận bằng ít nhất hai probe và/hoặc lập luận | **Chưa hoàn tất** |
| P1 | 75 câu NB trong 1.000 câu; độ khó chưa phù hợp học sinh yếu | Tăng tỉ trọng câu NB/TH trong phiên củng cố và viết câu hỏi bắc cầu; kiểm tra lại nhãn độ khó bằng chuyên gia | **Chưa hoàn tất** |
| P1 | Câu gần trùng, thay số, lặp khuôn có thể tăng giả tạo số lượng | Đo tương đồng ngữ nghĩa, truy vết mục tiêu kiến thức và rà soát thủ công từng cụm | **Chưa hoàn tất** |
| P1 | Chưa có số liệu thống kê từ học sinh | Pilot độc lập, phân tích độ khó thực nghiệm, khả năng phân biệt, nhiễu, độ tin cậy, kiểm định chẩn đoán | **Chưa hoàn tất** |
| P0 phát hành | Lịch sử bài Đ/S cũ lưu chỉ số vị trí mệnh đề, có nguy cơ không tương thích nếu đổi thứ tự | Version hóa snapshot câu hỏi trong phiên hoặc lưu thứ tự gốc theo session; chưa đưa nhánh này lên production | **Chặn triển khai production cho đến khi giải quyết** |

## C. Nội dung hiệu chỉnh V5 có thể kiểm tra

- `audit/question_bank_v5_tf_rebalance.json`: danh sách **102 mã câu**, thứ tự ban đầu và thứ tự sau sửa; không thay mệnh đề/đáp án khoa học.
- `question_bank_v5_patch.py`: tích hợp sau `apply_content_audit` và `apply_student_formula_policy`, hậu kiểm lại 1.000 câu.
- `tests/test_question_v5_quality.py`: kiểm tra phân bố, 102 phép hoán vị hợp lệ, bảo toàn số đúng/sai từng câu, chống áp dụng nhầm phiên bản.
- `Dockerfile`: tích hợp bản V5 trên **nhánh riêng**.

### Phân bố mẫu mệnh đề Đ/S trước và sau

| Mẫu (Đ = Đúng, S = Sai) | Trước | Sau |
|---|---:|---:|
| ĐĐSS | 113 | 33 |
| ĐSĐS | 49 | 33 |
| ĐSSĐ | 3 | 33 |
| SĐĐS | 16 | 33 |
| SĐSĐ | 13 | 32 |
| SSĐĐ | 2 | 32 |
| ĐĐĐS | 6 | 6 |
| ĐĐSĐ | 12 | 6 |
| ĐSĐĐ | 4 | 5 |
| SĐĐĐ | 0 | 5 |

Tổng cộng cả trước và sau là 218 câu. **V5 giảm khả năng đoán mẫu vị trí**, chưa giải quyết **tính dự đoán về số lượng mệnh đề đúng**.

## D. Giới hạn bắt buộc công bố

- Chưa có bằng chứng đã xác minh độc lập **1.000/1.000** câu với từng trang SGK hoặc đã thẩm định toàn bộ về mặt ngữ nghĩa.
- Chưa chứng minh 67 mã lỗi có độ nhạy/đặc hiệu bằng dữ liệu học sinh.
- Các thay đổi V5 hiện là **nhánh thử nghiệm chờ kiểm chứng tích hợp và tương thích lịch sử**, không phải bản đã đưa lên hệ thống public.
- Không được dùng các chỉ số `issues=[]` của bản V4 để tuyên bố “hết mọi nhược điểm” về chẩn đoán.
