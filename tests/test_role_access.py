"""Portal and classroom authorization regressions for the generated bundle.

Run with PHY_APP_ROOT pointing to the patched application directory. These tests
use their own database and never start the application against its runtime data.
"""

import csv
import hashlib
import io
import os
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


APP_ROOT = os.environ.get("PHY_APP_ROOT")
if not APP_ROOT:
    pytest.skip("Set PHY_APP_ROOT to the generated application root", allow_module_level=True)
sys.path.insert(0, str(Path(APP_ROOT).resolve()))
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "role-access-regression-secret-only"
os.environ["DATABASE_URL"] = "sqlite://"

from app.auth import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Classroom, Enrollment, LearningSession, TeacherLabel, User


PASSWORD = "RoleTestPassword123"


@pytest.fixture(scope="session")
def password_hash():
    return hash_password(PASSWORD)


@pytest.fixture
def context(password_hash):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as db:
        users = {}
        for user_id, role in [
            ("teacher_a", "teacher"), ("teacher_b", "teacher"), ("admin", "admin"),
            ("student_a", "student"), ("student_b", "student"),
            ("unenrolled", "student"), ("shared", "student"),
        ]:
            users[user_id] = User(
                id=user_id, username=user_id, display_name=user_id,
                password_hash=password_hash, role=role,
            )
        db.add_all(users.values())
        db.add_all([
            Classroom(id="class_a", name="12A1", join_code="CODE_A", teacher_id="teacher_a"),
            Classroom(id="class_b", name="12A2", join_code="CODE_B", teacher_id="teacher_b"),
        ])
        db.flush()
        db.add_all([
            Enrollment(user_id="student_a", classroom_id="class_a"),
            Enrollment(user_id="student_b", classroom_id="class_b"),
            Enrollment(user_id="shared", classroom_id="class_a"),
            Enrollment(user_id="shared", classroom_id="class_b"),
        ])
        db.add_all([
            LearningSession(id="diagnostic_a", user_id="student_a", kind="diagnostic"),
            LearningSession(id="diagnostic_b", user_id="student_b", kind="diagnostic"),
            LearningSession(id="practice_a", user_id="student_a", kind="practice"),
        ])
        db.commit()
        headers = {
            key: {"Authorization": "Bearer " + create_access_token(user)}
            for key, user in users.items()
        }

    def isolated_db():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = isolated_db
    # The lifespan is intentionally omitted; its account bootstrap uses the
    # runtime engine rather than our dependency override.
    client = TestClient(app)
    yield client, headers, sessions
    client.close()
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def login(client, username, *, password=PASSWORD, portal=None, include_portal=True):
    payload = {"username": username, "password": password}
    if include_portal:
        payload["portal"] = portal
    return client.post("/api/auth/login", json=payload)


@pytest.mark.parametrize("username,portal", [
    ("student_a", "student"), ("teacher_a", "teacher"), ("admin", "teacher"),
])
def test_matching_portal_and_admin_login(context, username, portal):
    client, _, _ = context
    response = login(client, username, portal=portal)
    assert response.status_code == 200
    assert response.json()["user"]["username"] == username
    assert response.json()["token"]


@pytest.mark.parametrize("username,portal", [
    ("student_a", "teacher"), ("teacher_a", "student"), ("admin", "student"),
])
def test_correct_password_cannot_enter_other_portal(context, username, portal):
    client, _, _ = context
    response = login(client, username, portal=portal)
    assert response.status_code == 403
    assert "Vui lòng đăng nhập ở mục" in response.json()["detail"]
    assert "token" not in response.json()


@pytest.mark.parametrize("username,portal", [
    ("student_a", "teacher"), ("teacher_a", "student"), ("missing_user", "student"),
])
def test_bad_credentials_do_not_disclose_role(context, username, portal):
    client, _, _ = context
    response = login(client, username, password="incorrect-password", portal=portal)
    assert response.status_code == 401
    assert response.json()["detail"] == "Tên đăng nhập hoặc mật khẩu không đúng"


@pytest.mark.parametrize("username", ["student_a", "teacher_a", "admin"])
@pytest.mark.parametrize("include_portal", [False, True])
def test_existing_login_clients_remain_supported(context, username, include_portal):
    client, _, _ = context
    assert login(client, username, include_portal=include_portal).status_code == 200


def test_unknown_portal_is_rejected(context):
    client, _, _ = context
    assert login(client, "student_a", portal="admin").status_code == 422


def test_locked_account_cannot_enter_matching_portal(context):
    client, _, sessions = context
    with sessions() as db:
        db.get(User, "teacher_a").is_active = False
        db.commit()
    assert login(client, "teacher_a", portal="teacher").status_code == 403


@pytest.mark.parametrize("who,expected", [
    ("teacher_a", {"class_a"}), ("teacher_b", {"class_b"}),
    ("student_a", {"class_a"}), ("admin", {"class_a", "class_b"}),
])
def test_class_list_follows_membership_and_teacher_ownership(context, who, expected):
    client, headers, _ = context
    response = client.get("/api/classes", headers=headers[who])
    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == expected


CLASS_PATHS = [
    "/api/teacher/classes/{class_id}/dashboard",
    "/api/teacher/v2/classes/{class_id}/dashboard",
    "/api/teacher/classes/{class_id}/export.csv",
]


@pytest.mark.parametrize("path", CLASS_PATHS)
def test_teacher_can_only_read_own_class(context, path):
    client, headers, _ = context
    own = client.get(path.format(class_id="class_a"), headers=headers["teacher_a"])
    assert own.status_code == 200
    if path.endswith("dashboard"):
        assert {s["id"] for s in own.json()["student_progress"]} == {"student_a", "shared"}
    foreign = client.get(path.format(class_id="class_b"), headers=headers["teacher_a"])
    assert foreign.status_code == 404
    assert client.get(path.format(class_id="class_b"), headers=headers["admin"]).status_code == 200
    assert client.get(path.format(class_id="class_a"), headers=headers["student_a"]).status_code == 403


STUDENT_PATHS = [
    "/api/teacher/students/{student_id}/progress",
    "/api/teacher/v2/students/{student_id}/progress",
    "/api/teacher/v2/students/{student_id}/report.csv",
]


@pytest.mark.parametrize("path", STUDENT_PATHS)
def test_teacher_student_details_are_scoped_to_current_enrollment(context, path):
    client, headers, _ = context
    for student_id in ("student_a", "shared"):
        assert client.get(path.format(student_id=student_id), headers=headers["teacher_a"]).status_code == 200
    for student_id in ("student_b", "unenrolled"):
        assert client.get(path.format(student_id=student_id), headers=headers["teacher_a"]).status_code == 403
    assert client.get(path.format(student_id="student_b"), headers=headers["admin"]).status_code == 200
    assert client.get(path.format(student_id="student_a"), headers=headers["student_a"]).status_code == 403
    # Student report routes must not expose staff accounts, even to admins.
    assert client.get(path.format(student_id="teacher_b"), headers=headers["admin"]).status_code == 404


def test_password_reset_cannot_change_foreign_students(context):
    client, headers, _ = context
    new_password = "ChangedByOwnTeacher123"
    path = "/api/teacher/v2/students/{student_id}/reset-password"
    own = client.post(path.format(student_id="student_a"), json={"new_password": new_password}, headers=headers["teacher_a"])
    assert own.status_code == 200
    assert login(client, "student_a", password=new_password, portal="student").status_code == 200
    foreign = client.post(path.format(student_id="student_b"), json={"new_password": new_password}, headers=headers["teacher_a"])
    assert foreign.status_code == 403
    assert login(client, "student_b", portal="student").status_code == 200
    assert client.post(path.format(student_id="student_b"), json={"new_password": new_password}, headers=headers["admin"]).status_code == 200
    assert client.post(path.format(student_id="shared"), json={"new_password": new_password}, headers=headers["student_a"]).status_code == 403


def test_labels_require_current_student_and_own_diagnostic_session(context):
    client, headers, sessions = context
    payload = {"student_id": "student_a", "error_id": "TEST_ERROR", "label": 1}
    assert client.post("/api/teacher/labels", json=payload | {"diagnostic_session_id": "diagnostic_a"}, headers=headers["teacher_a"]).status_code == 200
    assert client.post("/api/teacher/labels", json=payload | {"student_id": "student_b"}, headers=headers["teacher_a"]).status_code == 403
    for session_id in ("diagnostic_b", "practice_a", "missing_session"):
        response = client.post("/api/teacher/labels", json=payload | {"diagnostic_session_id": session_id}, headers=headers["teacher_a"])
        assert response.status_code == 404
    assert client.post("/api/teacher/labels", json=payload | {"student_id": "teacher_b"}, headers=headers["admin"]).status_code == 404
    with sessions() as db:
        labels = db.execute(select(TeacherLabel)).scalars().all()
        assert [(label.student_id, label.diagnostic_session_id) for label in labels] == [("student_a", "diagnostic_a")]


def test_training_export_excludes_students_no_longer_taught_and_other_teachers_labels(context):
    client, headers, sessions = context
    with sessions() as db:
        db.add_all([
            TeacherLabel(teacher_id="teacher_a", student_id="student_a", error_id="OWN", label=1),
            TeacherLabel(teacher_id="teacher_a", student_id="student_b", error_id="FOREIGN", label=1),
            TeacherLabel(teacher_id="teacher_b", student_id="shared", error_id="OTHER_TEACHER", label=1),
        ])
        db.commit()
    response = client.get("/api/teacher/training-data.csv", headers=headers["teacher_a"])
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert [row["error_id"] for row in rows] == ["OWN"]
    assert rows[0]["student_id_hash"] == hashlib.sha256(b"student_a").hexdigest()[:20]
    with sessions() as db:
        db.execute(delete(Enrollment).where(Enrollment.user_id == "student_a"))
        db.commit()
    # Existing tokens must not retain access after enrollment is removed.
    assert client.get("/api/teacher/v2/students/student_a/progress", headers=headers["teacher_a"]).status_code == 403
    response = client.get("/api/teacher/training-data.csv", headers=headers["teacher_a"])
    assert list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")))) == []
    admin_export = client.get("/api/teacher/training-data.csv", headers=headers["admin"])
    assert len(list(csv.DictReader(io.StringIO(admin_export.content.decode("utf-8-sig"))))) == 3


def test_rosters_exclude_staff_even_if_staff_has_an_enrollment(context):
    client, headers, sessions = context
    with sessions() as db:
        db.add(Enrollment(user_id="teacher_b", classroom_id="class_a"))
        db.commit()
    for path in CLASS_PATHS[:2]:
        response = client.get(path.format(class_id="class_a"), headers=headers["teacher_a"])
        assert response.status_code == 200
        assert {row["id"] for row in response.json()["student_progress"]} == {"student_a", "shared"}
        assert response.json()["stats"]["students"] == 2


def test_same_school_overview_is_preserved_but_management_requires_owned_class(context):
    client, headers, _ = context
    created = client.post("/api/schools", json={"name": "Trường THPT kiểm thử"}, headers=headers["teacher_a"])
    assert created.status_code == 200
    school = created.json()
    joined = client.post("/api/schools/join", json={"code": school["code"]}, headers=headers["teacher_b"])
    assert joined.status_code == 200

    # Joining a school attaches the teacher's existing classes and preserves
    # the school's shared student overview, including classes taught by peers.
    response = client.get(f"/api/teacher/schools/{school['id']}/dashboard", headers=headers["teacher_a"])
    assert response.status_code == 200
    dashboard = response.json()
    assert dashboard["stats"]["teachers"] == 2
    assert {row["id"] for row in dashboard["classes"]} == {"class_a", "class_b"}
    assert {row["id"] for row in dashboard["students"]} == {"student_a", "student_b", "shared"}
    assert client.get("/api/teacher/students/student_b/progress", headers=headers["teacher_a"]).status_code == 200
    assert client.get("/api/teacher/students/unenrolled/progress", headers=headers["teacher_a"]).status_code == 403

    assert client.get("/api/teacher/v2/students/student_b/progress", headers=headers["teacher_a"]).status_code == 403
    assert client.get("/api/teacher/v2/students/student_b/report.csv", headers=headers["teacher_a"]).status_code == 403
    assert client.get("/api/teacher/classes/class_b/export.csv", headers=headers["teacher_a"]).status_code == 404
    response = client.post("/api/teacher/v2/students/student_b/reset-password", json={"new_password": "UnauthorizedChange123"}, headers=headers["teacher_a"])
    assert response.status_code == 403
    assert login(client, "student_b", portal="student").status_code == 200
    response = client.post("/api/teacher/labels", json={"student_id": "student_b", "error_id": "TEST_ERROR", "label": 1}, headers=headers["teacher_a"])
    assert response.status_code == 403


def test_school_class_creation_join_and_student_dashboard_remain_available(context):
    client, headers, _ = context
    school = client.post("/api/schools", json={"name": "Trường THPT kiểm thử"}, headers=headers["teacher_a"]).json()
    response = client.post(f"/api/schools/{school['id']}/classes", json={"name": "12A3"}, headers=headers["teacher_a"])
    assert response.status_code == 200
    classroom = response.json()
    joined = client.post("/api/classes/join", json={"join_code": classroom["join_code"]}, headers=headers["unenrolled"])
    assert joined.status_code == 200
    dashboard = client.get("/api/student/dashboard", headers=headers["unenrolled"])
    assert dashboard.status_code == 200
    assert dashboard.json()["schools"] == [{"id": school["id"], "name": school["name"]}]
    assert {row["id"] for row in dashboard.json()["classes"]} == {classroom["id"]}
    # A teacher outside this school cannot create its classes or read it.
    assert client.post(f"/api/schools/{school['id']}/classes", json={"name": "12A4"}, headers=headers["teacher_b"]).status_code == 403
    assert client.get(f"/api/teacher/schools/{school['id']}/dashboard", headers=headers["teacher_b"]).status_code == 403
