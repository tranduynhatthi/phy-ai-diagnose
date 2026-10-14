"""Ensure student decluttering does not break class data or AI actions."""
from pathlib import Path
import importlib.util
import os

ROOT = Path(os.environ.get("PHY_APP_ROOT", "/app"))
PATCH = Path("/tmp/student_ui_cleanup_patch.py")
spec = importlib.util.spec_from_file_location("student_ui_cleanup_patch", PATCH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_only_student_class_panel_is_hidden():
    html = """<html><head></head><body>
    <section id="teacherView"><div class="card"><h2>Lớp học</h2></div></section>
    <section id="studentView"><div class="card" id="studentClassesCard">
      <h2>Lớp học</h2><form><input id="joinCode"><button>Tham gia</button></form>
    </div><div class="card" id="diagnosticCard"><h2>Chẩn đoán</h2></div></section>
    </body></html>"""
    out = module.simplify(html)
    assert out.count('data-student-class-panel="hidden"') == 2  # card + CSS rule
    assert '<div class="card" id="studentClassesCard" data-student-class-panel="hidden"' in out
    assert '<section id="teacherView"><div class="card"><h2>Lớp học' in out
    assert 'id="joinCode"' in out
    assert 'id="diagnosticCard"' in out
    assert module.simplify(out) == out


def test_deployed_student_html_has_no_redundant_messages():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    assert 'data-student-class-panel="hidden"' in html
    assert 'id="student-ui-cleanup"' in html
    assert "function renderAiCoach(" in html
    assert "function socraticLauncher(" in html
    assert "Sửa lỗi này ngay" in html
    for verbose in (
        "Hệ thống đã xác định các điểm cần ưu tiên từ bằng chứng",
        "AI Coach tạm thời chưa khả dụng",
        "✓ Evidence Engine đã kiểm chứng lỗi này trước khi AI lập kế hoạch",
        "AI không tự quyết định em mắc lỗi",
        "1 · Gemini đọc lập luận",
    ):
        assert verbose not in html
