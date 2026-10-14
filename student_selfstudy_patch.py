from pathlib import Path
import re

ROOT = Path("/app")
main_path = ROOT / "app/main.py"
bank_path = ROOT / "app/question_bank.py"
policy_path = ROOT / "app/student_selfstudy_policy.py"
html_path = ROOT / "app/static/index.html"

POLICY = r'''"""Student-first release policy for PHY-AI DIAGNOSE v1.4."""
import re

FORMULA_RULES = [
    (r"\\bbiết\\s*E0\\s*=\\s*NBS\\s*[·⋅*]?\\s*2πf\\s*và\\s*E\\s*=\\s*E0\\s*/\\s*√2\\s*[,.]?", "vận dụng các hệ thức của máy phát điện xoay chiều đã học."),
    (r"\\bĐiện áp hiệu dụng đầu máy phát coi bằng\\s*E0\\s*/\\s*√2\\s*,\\s*với\\s*E0\\s*=\\s*NBS\\s*[·⋅*]?\\s*2πf\\s*[,.]?", "Vận dụng các hệ thức của máy phát điện xoay chiều đã học."),
    (r"\\bGiá trị hiệu dụng\\s*E\\s*=\\s*E0\\s*/\\s*√2\\s*bằng bao nhiêu\\?", "Giá trị hiệu dụng bằng bao nhiêu?"),
    (r"\\bBiên độ suất điện động\\s*E0\\s*=\\s*NBS\\s*[·⋅*]?\\s*2πf\\s*bằng bao nhiêu\\?", "Biên độ suất điện động bằng bao nhiêu?"),
    (r"\\bDùng\\s+p\\s*=\\s*ρ\\s*⟨v²⟩\\s*/\\s*3\\s*[,.]?", "Vận dụng hệ thức thuyết động học phân tử đã học."),
    (r"\\s+và\\s*(?:Ē|E_bar|E)\\s*=\\s*3\\s*k\\s*T\\s*/\\s*2\\s*[,.]?", ""),
    (r"(?:Trong bài toán,\\s*)?(?:lấy|dùng)\\s+(?:hệ thức\\s+)?gần đúng\\s*T\\s*\\(K\\)\\s*[≈=]\\s*t\\s*\\(°C\\)\\s*\\+\\s*273\\s*[,.]?", ""),
    # Chapter I - thermal physics
    (r"\b(?:Với|Theo|Dùng)\s+quy\s+ước\s*ΔU\s*=\s*A\s*\+\s*Q\b", "Theo quy ước dấu của SGK"),
    (r"\btheo\s+quy\s+ước\s*ΔU\s*=\s*A\s*\+\s*Q\b", "theo quy ước dấu của SGK"),
    (r"\bNếu biểu diễn cùng nhiệt độ này theo thang Kelvin và dùng\s*T\s*\(K\)\s*=\s*t\s*\(°C\)\s*\+\s*273\s*,?", "Nếu biểu diễn cùng nhiệt độ này theo thang Kelvin,"),
    (r"\bDùng\s+(?:hệ thức|quy ước)\s+gần đúng\s*T\s*\(K\)\s*=\s*t\s*\(°C\)\s*\+\s*273\s*[,\.]?", ""),
    (r"\bDùng\s+(?:hệ thức|quy ước)\s+gần đúng\s*T\s*=\s*t\s*\+\s*273\s*[,\.]?", ""),
    (r"\bDùng\s+t\s*=\s*T\s*[-−]\s*273\s*[,\.]?", ""),
    (r"\bDùng\s+hệ thức\s+gần đúng\s*t\s*\(°C\)\s*=\s*T\s*\(K\)\s*[-−]\s*273\s*[,\.]?", ""),
    (r"học sinh dùng hệ thức\s*Q\s*=\s*m\s*c\s*ΔT\s*để xử lí", "học sinh xử lí"),
    (r"nhiệt lượng chuyển thể được tính bằng\s*Q\s*=\s*m\s*λ\.\s*Từ ý nghĩa các đại lượng trong hệ thức này,\s*", ""),
    (r"nhiệt lượng chuyển thể được tính bằng\s*Q\s*=\s*m\s*L\.\s*Từ hệ thức này,\s*", ""),
    # Chapter II - ideal gas
    (r"cần hiểu đúng quan hệ\s*pV\s*=\s*hằng số\s*và", "cần hiểu đúng mối liên hệ giữa áp suất, thể tích và"),
    (r"\bTrong phương trình trạng thái của khí lí tưởng\s*pV\s*=\s*nRT\s*,", "Trong phương trình Clapeyron của khí lí tưởng,"),
    (r"\bKhi áp dụng\s*pV\s*=\s*nRT\s*,", "Khi áp dụng phương trình Clapeyron,"),
    (r"\bHãy dùng phương trình\s*pV\s*=\s*nRT\s*để", "Hãy vận dụng phương trình Clapeyron để"),
    (r"\bđược mô tả bằng phương trình\s*pV\s*=\s*nRT\s*;?", "tuân theo phương trình Clapeyron;"),
    (r"\bDùng\s*pV\s*=\s*nRT\s*,", "Vận dụng phương trình Clapeyron,"),
    (r"\bquan hệ\s*pV\s*/\s*T\s*=\s*hằng số", "quan hệ trạng thái áp dụng cho cùng một lượng khí"),
    (r"\bMột bài toán kết hợp\s*pV\s*/\s*T\s*,\s*số mol và phương trình\s*pV\s*=\s*nRT\s*\.", "Một bài toán kết hợp phương trình trạng thái của khí lí tưởng và số mol."),
    (r"\bhệ thức\s*V1\s*/\s*T1\s*=\s*V2\s*/\s*T2", "định luật Charles"),
    # Chapter III - magnetism / AC
    (r"\bHãy dùng\s*F\s*=\s*BIl\s*sin\s*α\s*để", "Hãy vận dụng hệ thức lực từ đã học để"),
    (r"\bTính\s*F\s*=\s*BIl\s*sin\s*α\s*\.?", "Tính độ lớn lực từ tác dụng lên đoạn dây."),
    (r"phân biệt góc trong\s*F\s*=\s*BIl\s*sin\s*α\s*và góc trong\s*Φ\s*=\s*BS\s*cos\s*α", "phân biệt góc dùng trong hệ thức lực từ và góc dùng trong hệ thức từ thông"),
    (r"\bcó dạng\s*e\s*=\s*E0\s*cos\s*\(ωt\s*\+\s*φ\)\s*;?", "biến thiên điều hòa theo thời gian;"),
    (r"\btạo ra suất điện động hình sin\s*e\s*=\s*E0\s*cos\s*\(ωt\s*\+\s*φ\)\.", "tạo ra suất điện động xoay chiều biến thiên điều hòa theo thời gian."),
    # Chapter IV - nuclear physics
    (r"\bBán kính hạt nhân được mô tả gần đúng theo\s*R\s*=\s*R0\s*A\s*\^\s*\(1/3\)\.", "Bán kính hạt nhân phụ thuộc vào số khối theo quy luật đã học."),
    (r"\bDùng hệ thức gần đúng\s*R\s*=\s*R0\s*A\s*\^\s*\(1/3\)\.", "Vận dụng quy luật phụ thuộc bán kính hạt nhân vào số khối đã học."),
    (r"\bbằng quy luật\s*R\s*=\s*R0\s*A\s*\^\s*\(1/3\)", "bằng quy luật phụ thuộc bán kính hạt nhân vào số khối đã học"),
    (r"\bsử dụng đơn vị u và quy luật\s*R\s*=\s*R0\s*A\s*\^\s*\(1/3\)", "sử dụng đơn vị u và quy luật phụ thuộc bán kính hạt nhân vào số khối đã học"),
    (r"\bDùng\s*A\s*=\s*λN\s*,\s*λ\s*=\s*ln2\s*/\s*T\s*\.?", "Vận dụng các hệ thức về hoạt độ và chu kì bán rã đã học."),
    (r"\bDùng\s*λ\s*=\s*ln2\s*/\s*T\s*và\s*A\s*=\s*λN\s*\.?", "Vận dụng các hệ thức về hoạt độ và chu kì bán rã đã học."),
]

def sanitize_formula_stem(prompt: str) -> str:
    text = str(prompt or "")
    literal_replacements = [
        ("Trong bài toán, lấy gần đúng T(K)≈t(°C)+273.", ""),
        (" và Ē = 3kT/2.", "."),
        (" và Ē=3kT/2.", "."),
        ("Dùng p = ρ⟨v²⟩/3.", "Vận dụng hệ thức thuyết động học phân tử đã học."),
        ("Dùng p=ρ⟨v²⟩/3.", "Vận dụng hệ thức thuyết động học phân tử đã học."),
        ("Biên độ suất điện động E0 = NBS·2πf bằng bao nhiêu?", "Biên độ suất điện động bằng bao nhiêu?"),
        ("Biên độ suất điện động E0=NBS·2πf bằng bao nhiêu?", "Biên độ suất điện động bằng bao nhiêu?"),
        ("Giá trị hiệu dụng E = E0/√2 bằng bao nhiêu?", "Giá trị hiệu dụng bằng bao nhiêu?"),
        ("Giá trị hiệu dụng E=E0/√2 bằng bao nhiêu?", "Giá trị hiệu dụng bằng bao nhiêu?"),
        ("Điện áp hiệu dụng đầu máy phát coi bằng E0/√2, với E0=NBS·2πf.", "Vận dụng các hệ thức của máy phát điện xoay chiều đã học."),
        ("biết E0=NBS·2πf và E=E0/√2.", "vận dụng các hệ thức của máy phát điện xoay chiều đã học."),
    ]
    for old, new in literal_replacements:
        text = text.replace(old, new)
    for pattern, replacement in FORMULA_RULES:
        text = re.sub(pattern, replacement, text, flags=re.I)
    text = re.sub(r"\s+([,.;:?])", r"\1", text)
    text = re.sub(r" {2,}", " ", text).strip()
    text = re.sub(r"^[,.;]\s*", "", text)
    if text:
        text = text[0].upper() + text[1:]
    return text

def apply_student_formula_policy(data: dict) -> int:
    changed = 0
    for q in data.get("questions", []):
        before = str(q.get("prompt") or "")
        after = sanitize_formula_stem(before)
        if after != before:
            q["prompt"] = after
            changed += 1
    data.setdefault("audit", {})["formula_stem_policy"] = {
        "policy": "Do not reproduce formulas already taught in the supplied Physics 12 textbook inside question stems.",
        "changed_prompts": changed,
    }
    return changed
'''

policy_path.write_text(POLICY, encoding="utf-8")

bank = bank_path.read_text(encoding="utf-8")
if "apply_student_formula_policy" not in bank:
    anchor = "        apply_content_audit(self.data)\n"
    if anchor not in bank:
        raise SystemExit("student-selfstudy: content audit hook not found")
    bank = bank.replace(
        anchor,
        anchor + "        from .student_selfstudy_policy import apply_student_formula_policy\n        apply_student_formula_policy(self.data)\n",
        1,
    )
    bank_path.write_text(bank, encoding="utf-8")

main = main_path.read_text(encoding="utf-8")
if "post_exam_diagnosis" not in main:
    marker = "    db.commit()\n    review=[]\n"
    insertion = """    db.commit()
    db.refresh(s, attribute_names=[\"responses\"])
    exam_profiles = diagnostic_profiles_from_session(db, s)
    post_exam_profiles = []
    for item in exam_profiles:
        err = bank.error_by_id.get(item.get(\"error_id\"), {})
        post_exam_profiles.append({
            **item,
            \"title\": err.get(\"title\", item.get(\"error_id\")),
            \"chapter\": err.get(\"chapter\"),
            \"lesson\": err.get(\"lesson\"),
        })
    chapter_scores = result.get(\"chapter_scores\", {})
    weak_chapter = None
    weak_rate = None
    for chapter, score_data in chapter_scores.items():
        maximum = float(score_data.get(\"max\") or 0)
        if maximum <= 0:
            continue
        rate = float(score_data.get(\"earned\") or 0) / maximum
        if weak_rate is None or rate < weak_rate:
            weak_rate = rate
            weak_chapter = chapter
    review=[]
"""
    if marker not in main:
        raise SystemExit("student-selfstudy: exam commit marker not found")
    main = main.replace(marker, insertion, 1)
    old_return = '    return {"session":public_session(s),"result":result,"review":review,"ability_after":recent_performance(db,student.id)}'
    new_return = '    return {"session":public_session(s),"result":result,"review":review,"ability_after":recent_performance(db,student.id),"post_exam_diagnosis":{"profiles":post_exam_profiles,"weak_chapter":weak_chapter,"weak_rate":round(weak_rate,4) if weak_rate is not None else None}}'
    if old_return not in main:
        raise SystemExit("student-selfstudy: exam return marker not found")
    main = main.replace(old_return, new_return, 1)
    main_path.write_text(main, encoding="utf-8")

html = html_path.read_text(encoding="utf-8")
html = html.replace("Tạo tài khoản học sinh. Nhập mã lớp giáo viên cung cấp để tham gia lớp của bạn.", "Tạo tài khoản để bắt đầu lộ trình tự học Vật lí 12 theo lỗi sai của chính em.")
html = html.replace("PHY-AI DIAGNOSE lưu tên đăng nhập, họ tên hiển thị, lớp, câu trả lời và kết quả học tập để tạo hồ sơ học tập và hỗ trợ giáo viên theo dõi tiến bộ.", "PHY-AI DIAGNOSE lưu tên đăng nhập, họ tên hiển thị, câu trả lời và kết quả học tập để tạo hồ sơ tự học, theo dõi tiến bộ và cá nhân hóa các phiên chẩn đoán – sửa lỗi.")

# Student-only public interface. Teacher/admin APIs remain server-side for maintenance.
html = re.sub(r'\s*<article class="portal-card teacher-portal"[\s\S]*?</article>', "", html, count=1)
html = re.sub(r'\s*<section id="teacherView"[\s\S]*?</section>', "", html, count=1)
html = html.replace("Chọn không gian của bạn", "Tự học Vật lí 12 theo lỗi sai của chính em")
html = html.replace(
    "Đăng nhập để tiếp tục học tập hoặc quản lí lớp học.<br>Hai không gian riêng, cùng một hành trình tiến bộ.",
    "Dành cho học sinh trung bình và yếu: làm bài, biết mình sai ở đâu, sửa đúng lỗi rồi kiểm tra lại bằng ngữ cảnh mới."
)
html = html.replace(
    "Ôn tập Vật lí, nhận diện lỗi tư duy và luyện tập theo tiến độ của bạn.",
    "Tự học theo lộ trình ngắn: chẩn đoán → sửa lỗi → luyện đề → chẩn đoán lại."
)
html = html.replace(
    '<ul class="portal-features" aria-label="Chức năng học sinh"><li>Ôn tập &amp; chẩn đoán</li><li>Luyện đề</li><li>Sửa lỗi tư duy</li></ul>',
    '<ul class="portal-features" aria-label="Chức năng học sinh"><li>Chẩn đoán lỗi</li><li>Sửa đúng lỗi</li><li>Luyện đề thích ứng</li><li>Tự kiểm tra tiến bộ</li></ul>'
)

# Remove class-code dependency from the public registration form while keeping JS compatibility.
html = re.sub(
    r'<div class="field"><label for="regClass">[\s\S]*?<input id="regClass"[^>]*></div>',
    '<input id="regClass" type="hidden" value="">',
    html,
    count=1,
)

# Student-first learning guide at the top of the dashboard.
if 'id="selfStudyGuide"' not in html:
    student_marker = '<section id="studentView"'
    start = html.find(student_marker)
    if start < 0:
        raise SystemExit("student-selfstudy: studentView not found")
    open_end = html.find(">", start) + 1
    guide = '''
 <div id="selfStudyGuide" class="card self-study-guide">
  <span class="pill">LỘ TRÌNH TỰ HỌC</span>
  <h2>Không cần học lại tất cả. Hãy sửa đúng chỗ em đang vướng.</h2>
  <div class="self-study-steps">
   <div><b>1. Chẩn đoán</b><span>Làm một phiên ngắn để tìm lỗi tư duy.</span></div>
   <div><b>2. Sửa lỗi</b><span>Học lại đúng khái niệm và làm bài chuyển giao.</span></div>
   <div><b>3. Luyện đề</b><span>Làm đề phù hợp năng lực hiện tại.</span></div>
   <div><b>4. Kiểm tra lại</b><span>Hệ thống xác nhận lỗi đã giảm trong ngữ cảnh mới.</span></div>
  </div>
 </div>'''
    html = html[:open_end] + guide + html[open_end:]

# Restore adaptive default for students who need scaffolding.
html = re.sub(
    r'<select id="examLevel">[\s\S]*?</select>',
    '<select id="examLevel"><option value="auto" selected>Tự động theo kết quả gần đây</option><option value="foundation">Củng cố nền tảng</option><option value="developing">Đang phát triển</option><option value="proficient">Khá – vững</option><option value="advanced">Nâng cao</option><option value="balanced">Cân bằng</option></select>',
    html,
    count=1,
)

# Larger reasoning/opinion collection field.
if 'id="student-selfstudy-styles"' not in html:
    styles = '''
<style id="student-selfstudy-styles">
#authView.auth{max-width:680px}
.portal-grid{grid-template-columns:1fr;max-width:620px;margin:0 auto}
#qReasoning{width:100%;min-height:160px;padding:14px 15px;border:1px solid var(--line);border-radius:12px;resize:vertical;font:inherit;font-size:15px;line-height:1.55;background:#fff}
#qReasoning:focus{outline:3px solid #fff0e5;border-color:var(--p)}
.self-study-guide{border-left:5px solid var(--p)}
.self-study-guide h2{margin:10px 0 14px}
.self-study-steps{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.self-study-steps>div{padding:12px;border-radius:12px;background:#fff7f1;border:1px solid var(--line)}
.self-study-steps b,.self-study-steps span{display:block}.self-study-steps span{font-size:12px;color:var(--muted);margin-top:5px;line-height:1.45}
.post-exam-path{margin-top:18px}.post-exam-path .row{margin-top:8px}
@media(max-width:760px){.self-study-steps{grid-template-columns:1fr 1fr}}
@media(max-width:480px){.self-study-steps{grid-template-columns:1fr}}
</style>'''
    html = html.replace("</head>", styles + "\n</head>", 1)

# Post-exam diagnosis and remediation panel.
if 'id="examDiagnosis"' not in html:
    marker = '<div id="examStats" class="stats"></div>'
    panel = marker + '''<div id="examDiagnosis" class="card post-exam-path">
 <span class="pill">CHẨN ĐOÁN SAU ĐỀ</span>
 <h3 style="margin:10px 0 6px">Sai ở đâu → sửa lỗi đó → kiểm tra lại</h3>
 <div id="examDiagnosisBody" class="list"></div>
 <div id="examDiagnosisAction" style="margin-top:12px"></div>
</div>'''
    if marker not in html:
        raise SystemExit("student-selfstudy: examStats marker not found")
    html = html.replace(marker, panel, 1)

submit_pattern = re.compile(r'^async function submitExam\(auto=false\)\{.*?\}\n', re.M)
match = submit_pattern.search(html)
if not match:
    raise SystemExit("student-selfstudy: submitExam function not found")
new_submit = r'''async function submitExam(auto=false){saveExamAnswer();if(!auto&&!confirm('Nộp bài?'))return;clearInterval(examTimerHandle);try{let elapsed=Math.round((Date.now()-examStarted)/1000);let r=await api(`/api/exams/${exam.session.id}/submit`,{method:'POST',body:JSON.stringify({answers:examAnswers,elapsed_seconds:elapsed})});$('examResultScore').textContent=`${Number(r.result.total).toFixed(2)}/10`;$('examStats').innerHTML=`<div class="stat"><b>${r.result.part1.toFixed(2)}</b><span>Phần I</span></div><div class="stat"><b>${r.result.part2.toFixed(2)}</b><span>Phần II</span></div><div class="stat"><b>${r.result.part3.toFixed(2)}</b><span>Phần III</span></div><div class="stat"><b>${r.review.length}</b><span>Câu cần xem</span></div>`;let pd=r.post_exam_diagnosis||{},profiles=pd.profiles||[];$('examDiagnosisBody').innerHTML=profiles.length?profiles.slice(0,5).map(p=>`<div class="row error-item"><div><b>${esc(p.error_id)} · ${esc(p.title||'Lỗi cần sửa')}</b><div class="small muted">${esc(p.lesson||p.chapter||'')} · ${esc(p.state||'Cần chú ý')} · ${Number(p.confidence||0).toFixed(0)}%</div></div><button class="btn secondary" onclick="startRepair('${esc(p.error_id)}')">Sửa lỗi ngay</button></div>`).join(''):'<div class="feedback good"><b>Chưa đủ bằng chứng để kết luận một lỗi tư duy cụ thể từ riêng đề này.</b><div class="small">Hệ thống không gán lỗi chỉ từ một đáp án sai. Em nên làm chẩn đoán sâu ở chương yếu nhất.</div></div>';$('examDiagnosisAction').innerHTML=pd.weak_chapter?`<button class="btn primary" onclick="startPostExamDiagnostic('${esc(pd.weak_chapter)}')">Chẩn đoán sâu ${esc(pd.weak_chapter)}</button>`:'';
$('examReview').innerHTML=r.review.slice(0,20).map(x=>`<div class="row"><b>${esc(x.question.lesson)}</b><div>${esc(x.question.prompt)}</div><div class="small muted">Đáp án: ${esc(Array.isArray(x.correct_answer)?x.correct_answer.map(v=>v?'Đ':'S').join(' · '):x.correct_answer)} ${esc(x.unit||'')}</div>${x.explain?`<div class="small" style="margin-top:6px">${esc(Array.isArray(x.explain)?x.explain.join(' '):x.explain)}</div>`:''}</div>`).join('');show('examResultView');loadProfile()}catch(e){alert(e.message)}}
'''
html = html[:match.start()] + new_submit + html[match.end():]

if "function startPostExamDiagnostic(" not in html:
    helper = r'''
async function startPostExamDiagnostic(chapter){try{mode='diagnostic';let x=await api('/api/practice/start',{method:'POST',body:JSON.stringify({chapter,scope:'chapter',lesson:null,mode:'diagnostic',intensity:'standard'})});session=x.session;questions=x.questions;qIndex=0;qAnswered=false;show('questionView');renderQuestion()}catch(e){alert(e.message)}}
'''
    boot_pos = html.rfind("boot();")
    if boot_pos < 0:
        raise SystemExit("student-selfstudy: boot marker not found")
    html = html[:boot_pos] + helper + "\n" + html[boot_pos:]

html_path.write_text(html, encoding="utf-8")
print("Student self-study v1.4 patch applied")
