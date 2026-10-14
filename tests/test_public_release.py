import os
from pathlib import Path
import sys

from fastapi.testclient import TestClient


APP_ROOT = os.environ.get("PHY_APP_ROOT")
if not APP_ROOT:
    raise RuntimeError("Set PHY_APP_ROOT to the assembled application")
sys.path.insert(0, str(Path(APP_ROOT).resolve()))

from app.main import app


def test_student_privacy_notice_is_visible_in_public_portal():
    html = (Path(APP_ROOT) / "app/static/index.html").read_text(encoding="utf-8")
    assert 'id="studentPrivacyNotice"' in html
    assert "không yêu cầu email hoặc số điện thoại" in html
    assert "không gửi họ tên hay tên đăng nhập" in html
    assert "AI chỉ tạo bằng chứng gợi ý" in html


def test_public_security_headers_cover_api_and_homepage():
    client = TestClient(app)
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert health.headers["referrer-policy"] == "same-origin"
    assert health.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert health.headers["cache-control"] == "no-store"
    assert health.headers["x-robots-tag"] == "noindex, nofollow"

    home = client.get("/")
    assert home.status_code == 200
    assert home.headers["cache-control"] == "no-cache"
    assert home.headers["x-frame-options"] == "DENY"
