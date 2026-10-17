import os
import re
from pathlib import Path
import sys

APP_ROOT = Path(os.environ.get("PHY_APP_ROOT", "/app")).resolve()
sys.path.insert(0, str(APP_ROOT))

import app.main as m
from app.student_selfstudy_policy import sanitize_formula_stem
import app.student_selfstudy_policy as policy


def test_public_interface_keeps_student_selfstudy_and_restores_teachers():
    html = (APP_ROOT / "app/static/index.html").read_text(encoding="utf-8")
    assert 'class="portal-card teacher-portal"' in html
    assert 'id="teacherView"' in html
    assert 'id="teacherLoginForm"' in html
    assert 'id="teacherAccountSwitch"' in html
    assert 'class="portal-card student-portal"' in html
    assert 'id="selfStudyGuide"' in html
    assert "Chọn cổng Giáo viên" in html
    assert "Không cần học lại tất cả" in html


def test_reasoning_box_is_large_enough_for_explanation():
    html = (APP_ROOT / "app/static/index.html").read_text(encoding="utf-8")
    assert 'id="qReasoning"' in html
    style = re.search(r"#qReasoning\{([^}]*)\}", html)
    assert style, "Missing qReasoning release style"
    block = style.group(1)
    height = re.search(r"min-height\s*:\s*(\d+)px", block)
    assert height and int(height.group(1)) >= 160
    assert "resize:vertical" in block.replace(" ", "")


def test_post_exam_diagnosis_and_repair_path_exists():
    html = (APP_ROOT / "app/static/index.html").read_text(encoding="utf-8")
    main = (APP_ROOT / "app/main.py").read_text(encoding="utf-8")
    assert 'id="examDiagnosis"' in html
    assert "startPostExamDiagnostic" in html
    assert "Sửa lỗi ngay" in html
    assert '"post_exam_diagnosis"' in main
    assert "diagnostic_profiles_from_session(db, s)" in main


def test_adaptive_exam_is_default_again():
    html = (APP_ROOT / "app/static/index.html").read_text(encoding="utf-8")
    assert '<option value="auto" selected>Tự động theo kết quả gần đây</option>' in html


def test_class_code_is_optional_for_selfstudy_and_existing_students_can_join():
    html = (APP_ROOT / "app/static/index.html").read_text(encoding="utf-8")
    assert 'id="regClass" name="class_code"' in html
    assert 'Mã lớp của giáo viên (không bắt buộc)' in html
    assert 'id="studentClassJoinPanel"' in html
    assert 'id="studentTeacherJoinCode"' in html
    assert 'joinTeacherClass()' in html
    assert 'loadMyTeacherClasses()' in html


def test_privacy_copy_matches_student_selfstudy_goal():
    html = (APP_ROOT / "app/static/index.html").read_text(encoding="utf-8")
    assert "hỗ trợ giáo viên theo dõi tiến bộ" not in html
    assert "hồ sơ tự học" in html


def test_formula_sanitizer_changes_known_sgk_formula_cues():
    examples = [
        "Dùng hệ thức gần đúng T(K) = t(°C) + 273, hãy tính nhiệt độ.",
        "Trong phương trình trạng thái của khí lí tưởng pV = nRT, hãy xác định số mol.",
        "Hãy dùng F = BIl sin α để tính lực từ.",
        "Bán kính hạt nhân được mô tả gần đúng theo R = R0 A^(1/3).",
        "Dùng λ = ln2/T và A = λN.",
    ]
    for item in examples:
        assert sanitize_formula_stem(item) != item


def test_effective_bank_has_no_taught_formula_leaks_in_prompts():
    patterns = [
        r"(?:ΔU|\\Delta U)\s*=\s*A\s*\+\s*Q",
        r"T\s*\(?K\)?\s*[≈=]\s*t\s*\(?°?C\)?\s*\+\s*273\b",
        r"t\s*\(?°?C\)?\s*[≈=]\s*T\s*\(?K\)?\s*[-−]\s*273\b",
        r"Q\s*=\s*m\s*c\s*(?:ΔT|\\Delta T)",
        r"Q\s*=\s*m\s*λ",
        r"Q\s*=\s*m\s*L",
        r"p\s*V\s*=\s*n\s*R\s*T",
        r"p\s*V\s*/\s*T\s*=\s*hằng\s*số",
        r"V\s*1\s*/\s*T\s*1\s*=\s*V\s*2\s*/\s*T\s*2",
        r"F\s*=\s*B\s*I\s*[lL]\s*(?:sin|\\sin)",
        r"(?:Φ|Phi)\s*=\s*B\s*S\s*(?:cos|\\cos)",
        r"e\s*=\s*E\s*0\s*(?:cos|\\cos)\s*\(",
        r"R\s*=\s*R\s*0\s*A\s*\^\s*\(?\s*1\s*/\s*3\s*\)?",
        r"(?:A|H)\s*=\s*λ\s*N",
        r"λ\s*=\s*ln\s*2\s*/\s*T",
    ]
    violations = []
    for q in m.bank.questions:
        prompt = str(q.get("prompt") or "").replace("₀","0").replace("₁","1").replace("₂","2")
        for pattern in patterns:
            if re.search(pattern, prompt, re.I):
                violations.append((q["id"], prompt))
                break
    assert not violations, violations[:20]


def test_teacher_workspace_contains_only_owned_class_features():
    html = (APP_ROOT / "app/static/index.html").read_text(encoding="utf-8")
    start = html.index('<section id="teacherView"')
    end = html.index("</section>", start)
    teacher = html[start:end]
    for control in ('schoolSelect','schoolIdentity','schoolDetailCard','schoolStats'):
        assert f'id="{control}"' not in teacher, control
    for control in ('classList', 'studentProgressRows', 'studentDetailCard'):
        assert f'id="{control}"' in teacher, control
    assert 'onclick="createClass()"' in teacher
    assert 'Lớp học của tôi' in teacher
    loader_start = html.index("async function loadTeacher()")
    loader_end = html.index("}", loader_start)
    loader = html[loader_start:loader_end]
    assert "await loadTeacherClassesBase()" in loader
    assert "await loadSchools()" not in loader
