import inspect
from pathlib import Path
import os

from app.services import grade_repair_item


def test_repair_grader_rejects_null_answer_without_crashing():
    # The production 5xx came from int(None) on a repair multiple-choice item.
    # A blank answer must simply grade as incorrect.
    item = {"type": "mcq", "answer": 0, "options": ["A", "B", "C", "D"]}
    out = grade_repair_item(item, None)
    assert isinstance(out, dict)
    assert out.get("is_fully_correct") is False


def test_repair_grader_has_explicit_none_guard():
    source = inspect.getsource(grade_repair_item)
    assert "answer is not None" in source


def test_ai_coach_ui_shows_four_stage_role_and_direct_repair_action():
    root = Path(os.environ.get("PHY_APP_ROOT", "/app"))
    html = (root / "app/static/index.html").read_text(encoding="utf-8")
    assert "Gemini đọc lập luận" in html
    assert "Evidence Engine kiểm chứng" in html
    assert "AI giải thích điểm nghẽn" in html
    assert "Lập kế hoạch sửa lỗi" in html
    assert "Evidence Engine đã kiểm chứng lỗi này trước khi AI lập kế hoạch" in html
    assert "Sửa lỗi này ngay" in html
