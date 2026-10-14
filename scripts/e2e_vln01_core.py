from __future__ import annotations

import itertools
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import delete, select

sys.path.insert(0, "/app")
import app.main as m


TEST_USERNAME = "phyai-smoke-mv5d9acp"
TARGET_ERROR = "VLN-01"


def emit(step, payload):
    print("E2E|" + step + "|" + json.dumps(payload, ensure_ascii=False, default=str), flush=True)


def solve_bank_question(q):
    qtype = q.get("type")
    if qtype == "mcq":
        for i in range(len(q.get("options", []))):
            if m.bank.grade(q, i).get("is_fully_correct"):
                return i
    elif qtype == "tf":
        n = len(q.get("statements", []))
        for vals in itertools.product([False, True], repeat=n):
            value = list(vals)
            if m.bank.grade(q, value).get("is_fully_correct"):
                return value
    elif qtype == "short":
        for key in ("answer", "correct_answer", "value"):
            if key in q:
                return q[key]
    raise RuntimeError(f"Cannot solve bank question {q.get('id')}")


def targeted_wrong(q):
    correct = solve_bank_question(q)
    if q.get("type") == "tf":
        wrong = list(correct)
        idx = None
        for i, st in enumerate(q.get("statements", [])):
            if TARGET_ERROR in json.dumps(st, ensure_ascii=False):
                idx = i
                break
        if idx is None and q.get("id") in {"EXT-01-T01", "EXT-01-T04"} and len(wrong) >= 3:
            idx = 2
        if idx is None:
            raise RuntimeError(f"No VLN-01 statement mapping in {q.get('id')}")
        wrong[idx] = not bool(wrong[idx])
        return wrong
    if q.get("type") == "mcq":
        correct_i = int(correct)
        # Prefer a wrong choice whose metadata contains VLN-01.
        for i, opt in enumerate(q.get("options", [])):
            if i != correct_i and TARGET_ERROR in json.dumps(opt, ensure_ascii=False):
                return i
        return 0 if correct_i != 0 else 1
    raise RuntimeError(f"Unsupported targeted question {q.get('id')}")


def solve_repair_item(item):
    qid = item.get("id")
    if qid in m.bank.by_id:
        return solve_bank_question(m.bank.by_id[qid])
    grader = m.grade_repair_item
    qtype = item.get("type")
    if qtype == "mcq":
        for i in range(len(item.get("options", []))):
            if grader(item, i).get("is_fully_correct"):
                return i
    elif qtype == "tf":
        n = len(item.get("statements", []))
        for vals in itertools.product([False, True], repeat=n):
            value = list(vals)
            if grader(item, value).get("is_fully_correct"):
                return value
    elif qtype == "short":
        for key in ("answer", "correct_answer", "value"):
            if key in item:
                return item[key]
    raise RuntimeError(f"Cannot solve repair item {qid}")


def error_from_profile(profile):
    return next((e for e in profile.get("errors", []) if e.get("error_id") == TARGET_ERROR), None)


db_gen = m.get_db()
db = next(db_gen)
created_sessions = []
baseline_profile = None
baseline_snapshot = None

try:
    student = db.execute(select(m.User).where(m.User.username == TEST_USERNAME)).scalar_one_or_none()
    if not student or student.role != "student":
        raise RuntimeError("Dedicated smoke-test student not found")
    emit("STUDENT", {"id": student.id, "username": student.username})

    baseline = m.profile(student=student, db=db)
    baseline_profile = db.execute(
        select(m.ErrorProfile).where(
            m.ErrorProfile.user_id == student.id,
            m.ErrorProfile.error_id == TARGET_ERROR,
        )
    ).scalar_one_or_none()
    if baseline_profile:
        baseline_snapshot = {
            "confidence": baseline_profile.confidence,
            "state": baseline_profile.state,
            "repair_state": baseline_profile.repair_state,
            "evidence_wrong": baseline_profile.evidence_wrong,
            "evidence_total": baseline_profile.evidence_total,
            "updated_at": baseline_profile.updated_at,
        }
    emit("PROFILE_BEFORE", {"vln01": error_from_profile(baseline)})

    # A real diagnostic must cover mapped misconceptions in one session.
    started = m.start_practice(
        req=m.StartPracticeRequest(
            chapter="Chương I",
            scope="lesson",
            lesson="Bài 1",
            mode="diagnostic",
            intensity="standard",
        ),
        student=student,
        db=db,
    )
    diag_id = started["session"]["id"]
    created_sessions.append(diag_id)
    questions = started["questions"]
    qids = [q["id"] for q in questions]
    targets = [qid for qid in qids if TARGET_ERROR in str(m.bank.by_id[qid])][:2]
    diag_meta = dict((db.get(m.LearningSession, diag_id).meta_json or {}))
    emit("DIAG_START", {
        "session_id": diag_id,
        "question_ids": qids,
        "targets": targets,
        "strategy": diag_meta.get("diagnostic_strategy"),
    })
    if len(targets) < 2:
        raise RuntimeError(f"Adaptive selector did not provide two VLN-01 probes: {qids}")

    ai_evidence = []
    for pq in questions:
        qid = pq["id"]
        q = m.bank.by_id[qid]
        is_target = qid in targets
        value = targeted_wrong(q) if is_target else solve_bank_question(q)
        reasoning = None
        if is_target:
            reasoning = (
                "Em nghĩ vật rắn đứng yên thì các hạt cấu tạo nên vật cũng đứng yên hoàn toàn; "
                "chuyển động nhiệt chỉ có ở chất lỏng và chất khí."
            )
        ans = m.answer_practice(
            session_id=diag_id,
            req=m.AnswerRequest(
                answer={"question_id": qid, "value": value},
                duration_ms=9000,
                reasoning=reasoning,
            ),
            student=student,
            db=db,
        )
        response_row = db.execute(
            select(m.Response).where(
                m.Response.session_id == diag_id,
                m.Response.question_id == qid,
            )
        ).scalar_one()
        stored = dict(response_row.answer_json or {})
        ai = ans.get("ai") or stored.get("ai_analysis") or {}
        actual_correct = bool(response_row.is_fully_correct)
        if is_target:
            raw_ai = stored.get("ai_analysis") or {}
            candidates = ai.get("signals") or raw_ai.get("candidate_errors") or []
            ai_evidence.append({
                "question_id": qid,
                "correct": actual_correct,
                "used": ai.get("used"),
                "provider": ai.get("provider"),
                "model": ai.get("model"),
                "request_id": ai.get("request_id"),
                "candidate_errors": candidates,
                "decision_authority": ai.get("decision_authority"),
                "status": ai.get("status"),
            })
        emit("DIAG_ANSWER", {
            "question_id": qid,
            "target": is_target,
            "correct": actual_correct,
            "ai_used": ai.get("used") if is_target else None,
            "request_id": ai.get("request_id") if is_target else None,
        })

    finished = m.finish_practice(session_id=diag_id, student=student, db=db)
    ai_coach = finished.get("ai_coach") or {}
    emit("DIAG_FINISH", {
        "session": finished.get("session"),
        "profiles": finished.get("profiles"),
        "ai_evidence": ai_evidence,
        "ai_coach": ai_coach,
    })
    if not ai_coach.get("used"):
        raise RuntimeError(f"Live Gemini AI Coach was not used: {ai_coach}")
    if ai_coach.get("provider") != "gemini" or not ai_coach.get("request_id"):
        raise RuntimeError(f"AI Coach provider/request audit missing: {ai_coach}")
    if ai_coach.get("decision_authority") != "Evidence Engine":
        raise RuntimeError(f"AI Coach authority is not Evidence Engine: {ai_coach}")
    if len(ai_coach.get("plan") or []) != 3:
        raise RuntimeError(f"AI Coach did not produce exactly three steps: {ai_coach}")
    verified_codes = {str(p.get("error_id") or "") for p in (finished.get("profiles") or [])}
    coach_codes = {str(p.get("error_code") or "") for p in (ai_coach.get("focus_errors") or [])}
    if coach_codes - verified_codes:
        raise RuntimeError(f"AI Coach surfaced unverified errors: coach={coach_codes}, verified={verified_codes}")
    if TARGET_ERROR not in coach_codes:
        raise RuntimeError(f"AI Coach did not focus on verified VLN-01: {ai_coach}")

    p1 = m.profile(student=student, db=db)
    v1 = error_from_profile(p1)
    emit("PROFILE_AFTER_DIAG", {"vln01": v1})
    if not v1:
        raise RuntimeError("VLN-01 not created")
    if int(v1.get("evidence_wrong") or 0) < 1:
        raise RuntimeError(f"VLN-01 has no deterministic wrong evidence: {v1}")
    if not any(x.get("used") and any(c.get("error_code") == TARGET_ERROR for c in (x.get("candidate_errors") or [])) for x in ai_evidence):
        raise RuntimeError(f"Gemini did not produce VLN-01 candidate evidence: {ai_evidence}")

    repair = m.start_repair(
        req=m.StartRepairRequest(error_id=TARGET_ERROR),
        student=student,
        db=db,
    )
    repair_id = repair["session"]["id"]
    created_sessions.append(repair_id)
    repair_row = db.get(m.LearningSession, repair_id)
    items = list((repair_row.meta_json or {}).get("items", []))
    item_by_id = {x["id"]: x for x in items}
    emit("REPAIR_START", {
        "session_id": repair_id,
        "error": repair.get("error"),
        "question_ids": [q["id"] for q in repair["questions"]],
    })

    for pq in repair["questions"]:
        qid = pq["id"]
        value = solve_repair_item(item_by_id[qid])
        ans = m.answer_repair(
            session_id=repair_id,
            req=m.AnswerRequest(
                answer={"question_id": qid, "value": value},
                duration_ms=7000,
            ),
            student=student,
            db=db,
        )
        emit("REPAIR_ANSWER", {"question_id": qid, "correct": ans.get("correct")})
        if not ans.get("correct"):
            raise RuntimeError(f"Repair answer unexpectedly wrong for {qid}")

    repair_finish = m.finish_repair(session_id=repair_id, student=student, db=db)
    emit("REPAIR_FINISH", repair_finish)
    if repair_finish.get("state") != "Đã sửa tốt":
        raise RuntimeError(f"Repair state not good: {repair_finish}")

    p2 = m.profile(student=student, db=db)
    v2 = error_from_profile(p2)
    emit("PROFILE_AFTER_REPAIR", {"vln01": v2})

    # A repaired ErrorProfile must trigger a targeted recheck immediately.
    recheck = m.start_practice(
        req=m.StartPracticeRequest(
            chapter="Chương I",
            scope="lesson",
            lesson="Bài 1",
            mode="diagnostic",
            intensity="standard",
        ),
        student=student,
        db=db,
    )
    re_id = recheck["session"]["id"]
    created_sessions.append(re_id)
    re_qids = [q["id"] for q in recheck["questions"]]
    re_targets = [qid for qid in re_qids if TARGET_ERROR in str(m.bank.by_id[qid])]
    re_meta = dict((db.get(m.LearningSession, re_id).meta_json or {}))
    emit("RECHECK_SELECT", {
        "session_id": re_id,
        "targets_found": re_targets,
        "strategy": re_meta.get("diagnostic_strategy"),
        "target_errors": re_meta.get("diagnostic_target_errors"),
    })
    if len(re_targets) < 2:
        raise RuntimeError(f"Targeted recheck did not include two VLN-01 probes: {re_qids}")
    if re_meta.get("diagnostic_strategy") != "profile_targeted":
        raise RuntimeError(f"Recheck did not use profile_targeted strategy: {re_meta}")

    for pq in recheck["questions"]:
        qid = pq["id"]
        m.answer_practice(
            session_id=re_id,
            req=m.AnswerRequest(
                answer={"question_id": qid, "value": solve_bank_question(m.bank.by_id[qid])},
                duration_ms=6500,
            ),
            student=student,
            db=db,
        )
        response_row = db.execute(
            select(m.Response).where(
                m.Response.session_id == re_id,
                m.Response.question_id == qid,
            )
        ).scalar_one()
        if not bool(response_row.is_fully_correct):
            raise RuntimeError(f"Recheck answer unexpectedly wrong for {qid}")

    re_finish = m.finish_practice(session_id=re_id, student=student, db=db)
    p3 = m.profile(student=student, db=db)
    v3 = error_from_profile(p3)
    emit("RECHECK_FINISH", {
        "session": re_finish.get("session"),
        "profiles_from_recheck": re_finish.get("profiles"),
        "vln01_after_recheck": v3,
    })
    if not v3:
        raise RuntimeError("VLN-01 profile disappeared instead of retaining auditable history")
    if float(v3.get("confidence") or 0) >= float(v2.get("confidence") or 0):
        raise RuntimeError(f"Clean recheck did not reduce VLN-01 confidence: before={v2}, after={v3}")
    if int(v3.get("evidence_total") or 0) < int(v2.get("evidence_total") or 0) + 2:
        raise RuntimeError(f"Clean recheck evidence was not added: before={v2}, after={v3}")
    if v3.get("repair_state") != "Đã sửa tốt":
        raise RuntimeError(f"Repair state regressed after clean recheck: {v3}")

    emit("E2E_SUMMARY", {
        "ok": True,
        "diagnostic_session_id": diag_id,
        "repair_session_id": repair_id,
        "recheck_session_id": re_id,
        "vln01_after_diagnostic": v1,
        "vln01_after_repair": v2,
        "vln01_after_recheck": v3,
        "repair_state": repair_finish.get("state"),
        "repair_score": repair_finish.get("repair_score"),
        "repair_total": repair_finish.get("total"),
        "ai_evidence": ai_evidence,
        "ai_coach": {
            "used": ai_coach.get("used"),
            "provider": ai_coach.get("provider"),
            "model": ai_coach.get("model"),
            "request_id": ai_coach.get("request_id"),
            "focus_errors": [x.get("error_code") for x in (ai_coach.get("focus_errors") or [])],
            "plan_steps": len(ai_coach.get("plan") or []),
            "decision_authority": ai_coach.get("decision_authority"),
        },
    })

finally:
    # Restore the dedicated smoke user to its pre-test state.
    try:
        if created_sessions:
            db.execute(delete(m.Response).where(m.Response.session_id.in_(created_sessions)))
            db.execute(delete(m.LearningSession).where(m.LearningSession.id.in_(created_sessions)))
        current = db.execute(
            select(m.ErrorProfile).where(
                m.ErrorProfile.user_id == student.id,
                m.ErrorProfile.error_id == TARGET_ERROR,
            )
        ).scalar_one_or_none() if 'student' in locals() else None
        if baseline_snapshot is None:
            if current is not None:
                db.delete(current)
        elif current is not None:
            for key, value in baseline_snapshot.items():
                setattr(current, key, value)
        db.commit()
        emit("CLEANUP", {"restored": True, "sessions_removed": created_sessions})
    except Exception as cleanup_exc:
        db.rollback()
        emit("CLEANUP", {"restored": False, "error": str(cleanup_exc)})
    db_gen.close()
