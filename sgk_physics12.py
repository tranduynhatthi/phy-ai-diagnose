"""SGK Vật lí 12 Kết nối tri thức: mục lục 25 bài đã đối chiếu PDF ảnh (126 trang).

Đây chỉ là chỉ mục bài/trang và câu hỏi gợi mở tự biên soạn; không phải OCR
toàn văn hoặc bằng chứng rằng mọi câu trả lời do AI tạo đều nằm trong SGK.
"""
import re

_ROWS = [
 (1,"Cấu trúc của chất. Sự chuyển thể",6,9),
 (2,"Nội năng. Định luật I của nhiệt động lực học",10,14),
 (3,"Nhiệt độ. Thang nhiệt độ – nhiệt kế",15,19),
 (4,"Nhiệt dung riêng",20,23),
 (5,"Nhiệt nóng chảy riêng",24,26),
 (6,"Nhiệt hoá hơi riêng",27,29),
 (7,"Bài tập về vật lí nhiệt",30,32),
 (8,"Mô hình động học phân tử chất khí",34,36),
 (9,"Định luật Boyle",37,40),
 (10,"Định luật Charles",41,44),
 (11,"Phương trình trạng thái của khí lí tưởng",45,47),
 (12,"Áp suất khí theo mô hình động học phân tử. Quan hệ giữa động năng phân tử và nhiệt độ",48,51),
 (13,"Bài tập về khí lí tưởng",52,54),
 (14,"Từ trường",56,60),
 (15,"Lực từ tác dụng lên dây dẫn mang dòng điện. Cảm ứng từ",61,65),
 (16,"Từ thông. Hiện tượng cảm ứng điện từ",66,71),
 (17,"Máy phát điện xoay chiều",72,77),
 (18,"Ứng dụng hiện tượng cảm ứng điện từ",78,81),
 (19,"Điện từ trường. Mô hình sóng điện từ",82,85),
 (20,"Bài tập về từ trường",86,89),
 (21,"Cấu trúc hạt nhân",91,95),
 (22,"Phản ứng hạt nhân và năng lượng liên kết",96,103),
 (23,"Hiện tượng phóng xạ",104,113),
 (24,"Công nghiệp hạt nhân",114,118),
 (25,"Bài tập về vật lí hạt nhân",119,122),
]
_QUESTIONS = {
 1:"Các hạt cấu tạo chất chuyển động như thế nào và điều đó liên quan gì đến sự chuyển thể?",
 2:"Khi nội năng thay đổi, em cần xét những cách truyền năng lượng nào?",
 3:"Em nhận biết hai vật cân bằng nhiệt dựa vào đâu?",
 4:"Khi cùng nhận nhiệt lượng, vì sao các chất có thể tăng nhiệt độ khác nhau?",
 5:"Trong khi nóng chảy, vật nhận năng lượng thì nhiệt độ có nhất thiết tăng không?",
 6:"Khi chất lỏng hoá hơi ở nhiệt độ sôi, năng lượng nhận thêm có vai trò gì?",
 7:"Trong bài toán có những quá trình nhiệt nào?",
 8:"Chuyển động và va chạm của phân tử liên quan thế nào đến áp suất khí?",
 9:"Khi nhiệt độ không đổi, áp suất thay đổi thế nào nếu thể tích giảm?",
 10:"Khi áp suất không đổi, thể tích liên hệ thế nào với nhiệt độ tuyệt đối?",
 11:"Những đại lượng nào cần xét nhất quán trong phương trình trạng thái?",
 12:"Nhiệt độ tuyệt đối liên hệ thế nào với động năng tịnh tiến trung bình của phân tử?",
 13:"Những đại lượng khí nào không đổi và những đại lượng nào biến thiên?",
 14:"Em dựa vào đâu để xác định hướng của đường sức từ?",
 15:"Góc nào quyết định độ lớn lực từ tác dụng lên dây dẫn?",
 16:"Khi nào từ thông qua một vòng dây biến thiên?",
 17:"Điều gì làm suất điện động của máy phát điện biến thiên theo thời gian?",
 18:"Vì sao máy biến áp cần từ thông biến thiên qua các cuộn dây?",
 19:"Điện trường biến thiên và từ trường biến thiên liên hệ thế nào?",
 20:"Em cần xác định chiều hay độ lớn trước khi giải bài từ trường?",
 21:"Số proton và số nucleon mô tả gì về hạt nhân?",
 22:"Trong phản ứng hạt nhân cần bảo toàn những đại lượng nào?",
 23:"Có dự đoán chính xác thời điểm phân rã của từng hạt nhân được không?",
 24:"Ứng dụng hạt nhân phải cân nhắc các biện pháp an toàn nào?",
 25:"Em kiểm tra định luật bảo toàn và đơn vị thế nào trước khi tính?",
}
def get_sgk_anchor(chapter: str | None, lesson: str | None) -> dict | None:
    match = re.search(r"(?i)\bbài\s*0*(\d{1,2})\b", lesson or "")
    if not match: return None
    number = int(match.group(1))
    if not 1 <= number <= 25: return None
    chapter_no = "I" if number <= 7 else "II" if number <= 13 else "III" if number <= 20 else "IV"
    if chapter and not re.search(r"(?i)\bchương\s*" + chapter_no + r"\b", chapter):
        return None
    n, title, first, last = _ROWS[number - 1]
    return {
        "book":"Vật lí 12 – Kết nối tri thức với cuộc sống",
        "lesson_number":n,"lesson":f"Bài {n}","title":title,
        "chapter":f"Chương {chapter_no}",
        "printed_pages":[first,last],"pdf_pages":[first+1,last+1],
        "guiding_question":_QUESTIONS[n],
        "provenance":"Đã đối chiếu chỉ mục SGK PDF 126 trang; câu gợi mở tự biên soạn, không phải trích dẫn nguyên văn.",
        "full_text_verified":False
    }
