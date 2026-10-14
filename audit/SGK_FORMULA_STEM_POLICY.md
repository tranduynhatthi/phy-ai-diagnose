# Chính sách câu dẫn theo SGK Vật lí 12 — PHY-AI DIAGNOSE v1.4

## Mục tiêu

Bản v1.4 ưu tiên học sinh trung bình và yếu tự học. Câu hỏi phải kiểm tra khả năng nhớ, chọn và vận dụng kiến thức; vì vậy không chép lại trong câu dẫn những công thức đã được dạy trực tiếp trong SGK Vật lí 12 mà dự án sử dụng.

Dữ kiện số, hằng số vật lí, đơn vị và công thức ngoài phạm vi đã học vẫn có thể được cung cấp khi cần để bài toán xác định và tự đủ dữ kiện.

## Nhóm công thức được kiểm duyệt

- Vật lí nhiệt: quy đổi Celsius–Kelvin; nguyên lí I nhiệt động lực học; nhiệt lượng làm thay đổi nhiệt độ; nhiệt nóng chảy riêng; nhiệt hóa hơi riêng.
- Khí lí tưởng: định luật Boyle; định luật Charles; phương trình trạng thái và phương trình Clapeyron; hệ thức áp suất theo thuyết động học phân tử; động năng tịnh tiến trung bình của phân tử khí.
- Từ trường và dòng điện xoay chiều: lực từ lên đoạn dây; từ thông; cảm ứng điện từ; biểu thức tức thời và giá trị hiệu dụng; các hệ thức máy phát điện xoay chiều, máy biến áp và sóng điện từ đã học.
- Vật lí hạt nhân: bán kính hạt nhân theo số khối; hệ thức khối lượng–năng lượng; độ hụt khối và năng lượng liên kết; năng lượng liên kết riêng; định luật phóng xạ, hằng số phóng xạ và hoạt độ.

## Quy tắc biên tập

Ví dụ không phù hợp: “Dùng pV = nRT để tính …”

Cách dùng trong v1.4: “Vận dụng phương trình Clapeyron để tính …”

Ví dụ không phù hợp: “Dùng T(K) = t(°C) + 273 …”

Cách dùng trong v1.4: yêu cầu học sinh tự thực hiện đổi thang nhiệt độ, không đưa sẵn hệ thức.

Ví dụ không phù hợp: “Dùng F = BIl sin α …”

Cách dùng trong v1.4: “Vận dụng hệ thức lực từ đã học …”

## Cơ chế kỹ thuật

student_selfstudy_policy.py được áp dụng sau lớp hậu kiểm nội dung hiện có và trước khi question bank được dùng để tạo phiên học. Release gate quét toàn bộ câu dẫn hiệu lực; nếu một mẫu công thức SGK bị phát hiện lại, regression test sẽ thất bại.

Các lời giải và phần sửa lỗi vẫn có thể hiển thị công thức sau khi học sinh trả lời, vì mục đích ở đó là giải thích và hỗ trợ tự sửa lỗi, không phải cung cấp sẵn công thức trong câu dẫn.
