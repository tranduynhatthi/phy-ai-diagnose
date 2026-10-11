"""Regression for the production cleanup that previously removed all login forms."""

import ast
import base64
import gzip
import importlib.util
import os
from pathlib import Path
import sys

import pytest


REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("homepage_cleanup", REPO / "homepage_cleanup_patch.py")
cleanup = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cleanup
spec.loader.exec_module(cleanup)


def production_landing():
    wrapper = ast.parse((REPO / "multi_school_home_patch.py").read_text())
    payload = next(node.value for node in ast.walk(wrapper) if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("H4s"))
    patch = ast.parse(gzip.decompress(base64.b64decode(payload)).decode())
    return next(node.value.value for node in patch.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "landing" for target in node.targets))


def test_actual_production_landing_keeps_authentication():
    landing = production_landing()
    html = '<html><body>' + landing + '<section id="studentView" class="hidden"><div id="studentHomeStats"></div></section><section id="teacherView" class="hidden"><select id="schoolSelect"></select></section></body></html>'
    result = cleanup.cleanup_homepage(html)
    for node_id in ("authView", "authForms", "loginUser", "loginPass", "regName", "regClass", "studentHomeStats", "schoolSelect"):
        assert result.count(f'id="{node_id}"') == 1
    assert cleanup.ROLE_HEADING not in result
    assert 'class="role-preview"' not in result
    assert "PHY-AI DIAGNOSE giúp học sinh" not in result
    assert "Học Vật lí có mục tiêu." in result
    assert cleanup.cleanup_homepage(result) == result


def test_only_target_elements_inside_auth_are_removed():
    html = '<section id="authView"><div class="role-preview"><div><p>Comparison</p></div></div><form><p>Đăng nhập</p><input id="loginUser"></form></section><section><div class="role-preview">Keep dashboard content</div></section>'
    result = cleanup.cleanup_homepage(html)
    assert '<form><p>Đăng nhập</p><input id="loginUser"></form>' in result
    assert 'Keep dashboard content' in result
    assert result.count('<section') == 2


def test_build_rejects_missing_authentication_section():
    with pytest.raises(ValueError, match="authView"):
        cleanup.cleanup_homepage('<section id="teacherView" class="hidden"></section>')


@pytest.mark.skipif(not os.environ.get("PHY_APP_ROOT"), reason="Requires the Docker-assembled application")
def test_assembled_homepage_keeps_role_forms_and_dashboards():
    html = (Path(os.environ["PHY_APP_ROOT"]) / "app/static/index.html").read_text()
    for node_id in ("authView", "studentHomeStats", "schoolSelect"):
        assert html.count(f'id="{node_id}"') == 1
    assert 'id="loginUser"' in html or ('id="teacherLoginUser"' in html and 'id="studentLoginUser"' in html)
    assert cleanup.ROLE_HEADING not in html
    assert 'class="role-preview"' not in html
