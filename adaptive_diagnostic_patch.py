from pathlib import Path

p = Path("/app/app/main.py")
text = p.read_text(encoding="utf-8")

old = '''@app.post("/api/practice/start")
def start_practice(req: StartPracticeRequest, student: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    if req.chapter not in bank.chapters: raise HTTPException(400,"Chương không hợp lệ")
    if req.scope not in ("lesson","chapter") or req.mode not in ("practice","diagnostic") or req.intensity not in ("quick","standard","full"):
        raise HTTPException(400,"Tham số phiên không hợp lệ")
    lesson=req.lesson if req.scope=="lesson" else None
    if lesson and lesson not in bank.chapters[req.chapter]["lessons"]: raise HTTPException(400,"Bài không thuộc chương")
    pool=bank.pool(req.chapter,req.scope,lesson,diagnostic_only=req.mode=="diagnostic")
    selected=bank.select_practice(pool,req.scope,req.intensity)
    if not selected: raise HTTPException(400,"Không có câu hỏi phù hợp")
    if len(selected)>settings.max_session_questions: selected=selected[:settings.max_session_questions]
    s=LearningSession(user_id=student.id,kind=req.mode,mode=req.mode,chapter=req.chapter,lesson=lesson or req.chapter,meta_json={"question_ids":[q["id"] for q in selected],"scope":req.scope,"intensity":req.intensity})
    db.add(s);db.commit();db.refresh(s)
    return {"session":public_session(s),"questions":[bank.public_question(q) for q in selected]}'''

new = '''def _question_error_codes(question: dict) -> set[str]:
    """Return ontology codes explicitly embedded in a question's metadata.

    The current audited bank stores misconception mappings inside question
    metadata (including statement-level metadata for true/false questions).
    Match against the finite ontology only, so arbitrary prompt text cannot
    create a new diagnostic target.
    """
    raw = str(question)
    return {str(code) for code in bank.error_by_id if str(code) in raw}


def _error_matches_scope(error: dict, chapter: str, lesson: str | None) -> bool:
    error_chapter = error.get("chapter")
    error_lesson = error.get("lesson")
    if error_chapter not in (None, "", chapter):
        return False
    if lesson and error_lesson not in (None, "", lesson):
        return False
    return True


def _diagnostic_select(
    db: Session,
    student: User,
    pool: list[dict],
    generic_selected: list[dict],
    chapter: str,
    lesson: str | None,
) -> tuple[list[dict], list[str], str]:
    """Add deterministic misconception coverage without changing session size.

    Existing profiles are the highest-priority targets, especially repaired
    profiles that need a real recheck. New students receive coverage across the
    lesson/chapter ontology instead of a purely random diagnostic sample.
    """
    if not generic_selected:
        return generic_selected, [], "generic"

    limit = min(len(generic_selected), int(settings.max_session_questions))
    if limit <= 0:
        return [], [], "generic"

    # Index only mappings that actually occur inside this diagnostic pool.
    by_error: dict[str, list[dict]] = {}
    for q in pool:
        for code in _question_error_codes(q):
            meta = bank.error_by_id.get(code) or {}
            if _error_matches_scope(meta, chapter, lesson):
                by_error.setdefault(code, []).append(q)
    for code, questions in by_error.items():
        questions.sort(key=lambda q: str(q.get("id", "")))

    profiles = db.execute(
        select(ErrorProfile).where(ErrorProfile.user_id == student.id)
    ).scalars().all()
    profiles = [
        prof for prof in profiles
        if prof.error_id in by_error
        and _error_matches_scope(bank.error_by_id.get(prof.error_id) or {}, chapter, lesson)
    ]
    profiles.sort(
        key=lambda prof: (
            0 if prof.repair_state == "Đã sửa tốt" else 1,
            -float(prof.confidence or 0.0),
            str(prof.error_id),
        )
    )

    selected: list[dict] = []
    used: set[str] = set()
    target_errors: list[str] = []

    def add(q: dict) -> bool:
        qid = str(q.get("id", ""))
        if not qid or qid in used or len(selected) >= limit:
            return False
        selected.append(q)
        used.add(qid)
        return True

    # 1) Existing/repaired profiles: require two independent probes whenever
    # the bank has them. This makes post-repair confirmation reliable.
    for prof in profiles:
        added = 0
        for q in by_error.get(prof.error_id, []):
            if add(q):
                added += 1
            if added >= 2 or len(selected) >= limit:
                break
        if added:
            target_errors.append(str(prof.error_id))
        if len(selected) >= limit:
            break

    # 2) New/remaining capacity: coverage-first round robin. Prefer one probe
    # per ontology code, then a second probe when room permits.
    coverage_codes = sorted(by_error)
    for pass_index in (0, 1):
        for code in coverage_codes:
            if len(selected) >= limit:
                break
            candidates = by_error.get(code, [])
            if pass_index >= len(candidates):
                continue
            # Pick the first unused mapped question; overlapping mappings may
            # already have covered this code through another target.
            for q in candidates[pass_index:]:
                if add(q):
                    break
        if len(selected) >= limit:
            break

    # 3) Preserve the existing selector's distribution for all remaining slots.
    for q in generic_selected:
        if not add(q):
            continue
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        for q in pool:
            if add(q) and len(selected) >= limit:
                break

    strategy = "profile_targeted" if profiles else "coverage_first"
    return selected, target_errors, strategy


@app.post("/api/practice/start")
def start_practice(req: StartPracticeRequest, student: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    if req.chapter not in bank.chapters: raise HTTPException(400,"Chương không hợp lệ")
    if req.scope not in ("lesson","chapter") or req.mode not in ("practice","diagnostic") or req.intensity not in ("quick","standard","full"):
        raise HTTPException(400,"Tham số phiên không hợp lệ")
    lesson=req.lesson if req.scope=="lesson" else None
    if lesson and lesson not in bank.chapters[req.chapter]["lessons"]: raise HTTPException(400,"Bài không thuộc chương")
    pool=bank.pool(req.chapter,req.scope,lesson,diagnostic_only=req.mode=="diagnostic")
    selected=bank.select_practice(pool,req.scope,req.intensity)
    diagnostic_targets: list[str] = []
    diagnostic_strategy = "generic"
    if req.mode == "diagnostic":
        selected, diagnostic_targets, diagnostic_strategy = _diagnostic_select(
            db, student, pool, selected, req.chapter, lesson
        )
    if not selected: raise HTTPException(400,"Không có câu hỏi phù hợp")
    if len(selected)>settings.max_session_questions: selected=selected[:settings.max_session_questions]
    meta={"question_ids":[q["id"] for q in selected],"scope":req.scope,"intensity":req.intensity}
    if req.mode == "diagnostic":
        meta["diagnostic_strategy"] = diagnostic_strategy
        meta["diagnostic_target_errors"] = diagnostic_targets
    s=LearningSession(user_id=student.id,kind=req.mode,mode=req.mode,chapter=req.chapter,lesson=lesson or req.chapter,meta_json=meta)
    db.add(s);db.commit();db.refresh(s)
    return {"session":public_session(s),"questions":[bank.public_question(q) for q in selected]}'''

if old not in text:
    raise SystemExit("start_practice block not found for adaptive diagnostic patch")

p.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Adaptive diagnostic selector patch applied")
