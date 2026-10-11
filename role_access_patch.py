"""Apply the separate login portals and classroom access rules to the bundled app."""

from pathlib import Path
import argparse


def _replace(source: str, old: str, new: str, *, count: int = 1) -> str:
    """Fail clearly on bundle changes, and permit rerunning an applied patch."""
    # Some replacements contain their old marker as a prefix. Ignore sections
    # already replaced so reruns do not duplicate fields or permission checks.
    pieces = source.split(new)
    actual = sum(piece.count(old) for piece in pieces)
    if actual == 0 and new in source:
        return source
    if actual != count:
        raise ValueError(f"Expected {count} patch markers, found {actual}: {old[:80]!r}")
    return new.join(piece.replace(old, new) for piece in pieces)


def apply_patch(app_root: str | Path = "/app") -> None:
    app_root = Path(app_root)
    schemas_path = app_root / "app" / "schemas.py"
    main_path = app_root / "app" / "main.py"
    schemas = schemas_path.read_text(encoding="utf-8")
    main = main_path.read_text(encoding="utf-8")

    schemas = _replace(schemas, "from typing import Any\n", "from typing import Any, Literal\n")
    schemas = _replace(
        schemas,
        "class LoginRequest(BaseModel):\n    username: str\n    password: str\n",
        "class LoginRequest(BaseModel):\n    username: str\n    password: str\n"
        "    portal: Literal[\"student\", \"teacher\"] | None = None\n",
    )
    main = _replace(
        main,
        '    if not u.is_active:\n        raise HTTPException(403,"Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên")\n',
        '    if not u.is_active:\n        raise HTTPException(403,"Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên")\n'
        '    if req.portal == "student" and u.role != "student":\n'
        '        raise HTTPException(403,"Tài khoản này không dành cho học sinh. Vui lòng đăng nhập ở mục Giáo viên.")\n'
        '    if req.portal == "teacher" and u.role not in ("teacher", "admin"):\n'
        '        raise HTTPException(403,"Tài khoản này không dành cho giáo viên. Vui lòng đăng nhập ở mục Học sinh.")\n',
    )

    helpers = '''def _teacher_class_or_404(db: Session, teacher: User, class_id: str) -> Classroom:
    classroom = db.get(Classroom, class_id)
    if not classroom or (teacher.role != "admin" and classroom.teacher_id != teacher.id):
        raise HTTPException(404, "Không tìm thấy lớp")
    return classroom


def _teacher_student_or_404(db: Session, teacher: User, student_id: str) -> User:
    student = db.get(User, student_id)
    if not student or student.role != "student":
        raise HTTPException(404, "Không tìm thấy học sinh")
    if teacher.role != "admin":
        enrollment = db.execute(
            select(Enrollment).join(Classroom, Classroom.id == Enrollment.classroom_id).where(
                Enrollment.user_id == student_id, Classroom.teacher_id == teacher.id
            )
        ).first()
        if not enrollment:
            raise HTTPException(403, "Học sinh không thuộc lớp của giáo viên")
    return student


'''
    marker = '@app.get("/api/teacher/classes/{class_id}/dashboard")\n'
    if "def _teacher_student_or_404(" not in main:
        main = _replace(main, marker, helpers + marker)
    main = _replace(
        main,
        '    c=db.get(Classroom,class_id)\n'
        '    if not c or (teacher.role=="teacher" and c.teacher_id!=teacher.id): raise HTTPException(404,"Không tìm thấy lớp")\n',
        '    c = _teacher_class_or_404(db, teacher, class_id)\n',
    )
    main = _replace(
        main,
        '    c=db.get(Classroom,class_id)\n'
        '    if not c or (teacher.role=="teacher" and c.teacher_id!=teacher.id):raise HTTPException(404,"Không tìm thấy lớp")\n',
        '    c = _teacher_class_or_404(db, teacher, class_id)\n',
    )
    # Keep the school's read-only overview and legacy student progress route.
    # Multi-school members may read that overview; password changes, class
    # exports, detailed reports and labels still require a current owned class.
    main = _replace(
        main,
        '    u=db.get(User,student_id)\n'
        '    if not u or u.role!="student":raise HTTPException(404,"Không tìm thấy học sinh")\n'
        '    if not _t_access(db,teacher,student_id):raise HTTPException(403,"Học sinh không thuộc lớp của giáo viên")\n',
        '    u = _teacher_student_or_404(db, teacher, student_id)\n',
        count=2,
    )
    main = _replace(
        main,
        '    u=db.get(User,student_id)\n'
        '    if not u or not _t_access(db,teacher,student_id):raise HTTPException(404,"Không tìm thấy học sinh")\n',
        '    u = _teacher_student_or_404(db, teacher, student_id)\n',
    )
    main = _replace(
        main,
        'select(User).join(Enrollment,Enrollment.user_id==User.id).where(Enrollment.classroom_id==class_id)',
        'select(User).join(Enrollment,Enrollment.user_id==User.id).where(Enrollment.classroom_id==class_id,User.role=="student")',
        count=2,
    )
    main = _replace(
        main,
        '    # Teacher must teach at least one class containing student unless admin.\n'
        '    if teacher.role!="admin":\n'
        '        ok=db.execute(select(Enrollment).join(Classroom,Classroom.id==Enrollment.classroom_id).where(Enrollment.user_id==req.student_id,Classroom.teacher_id==teacher.id)).first()\n'
        '        if not ok: raise HTTPException(403,"Học sinh không thuộc lớp của giáo viên")\n',
        '    _teacher_student_or_404(db, teacher, req.student_id)\n'
        '    if req.diagnostic_session_id:\n'
        '        diagnostic = db.get(LearningSession, req.diagnostic_session_id)\n'
        '        if not diagnostic or diagnostic.user_id != req.student_id or diagnostic.kind != "diagnostic":\n'
        '            raise HTTPException(404, "Không tìm thấy phiên chẩn đoán của học sinh")\n',
    )
    main = _replace(
        main,
        '    if teacher.role=="teacher":q=q.where(TeacherLabel.teacher_id==teacher.id)\n',
        '    if teacher.role == "teacher":\n'
        '        student_ids = select(Enrollment.user_id).join(\n'
        '            Classroom, Classroom.id == Enrollment.classroom_id\n'
        '        ).join(User, User.id == Enrollment.user_id).where(\n'
        '            Classroom.teacher_id == teacher.id, User.role == "student"\n'
        '        )\n'
        '        q = q.where(TeacherLabel.teacher_id == teacher.id, TeacherLabel.student_id.in_(student_ids))\n',
    )
    obsolete = '''def _t_access(db,teacher,student_id):
    if teacher.role=="admin": return True
    return bool(db.execute(select(Enrollment).join(Classroom,Classroom.id==Enrollment.classroom_id).where(Enrollment.user_id==student_id,Classroom.teacher_id==teacher.id)).first())

'''
    main = main.replace(obsolete, "")

    # Compute every replacement first so a changed bundle fails without a partial update.
    schemas_path.write_text(schemas, encoding="utf-8")
    main_path.write_text(main, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_root", nargs="?", default="/app")
    apply_patch(parser.parse_args().app_root)
