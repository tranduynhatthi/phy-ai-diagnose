from pathlib import Path

services = Path('/app/app/services.py')
s = services.read_text(encoding='utf-8')

old = '''        # Conservative rolling update.
        prof.confidence = round(prof.confidence*0.70 + final_c*0.30, 2) if prof.evidence_total else round(final_c,2)
        prof.state = state_from_confidence(prof.confidence) if state != "Đang xác minh" else state
        prof.evidence_wrong += e["wrong"]
        prof.evidence_total += e["total"]
        prof.updated_at = now_utc()'''
new = '''        # Conservative rolling update. Legacy rows may contain NULL values.
        prev_total = int(prof.evidence_total or 0)
        prev_wrong = int(prof.evidence_wrong or 0)
        prev_confidence = float(prof.confidence or 0.0)
        prof.confidence = round(prev_confidence*0.70 + final_c*0.30, 2) if prev_total else round(final_c,2)
        prof.state = state_from_confidence(prof.confidence) if state != "Đang xác minh" else state
        prof.evidence_wrong = prev_wrong + int(e["wrong"])
        prof.evidence_total = prev_total + int(e["total"])
        prof.updated_at = now_utc()'''
if old not in s:
    raise SystemExit('services diagnostic update block not found')
s = s.replace(old, new, 1)

s = s.replace(
    'if e and p.confidence >= 35:',
    'if e and float(p.confidence or 0) >= 35:',
    1
)
s = s.replace(
    'min(.12, .015 * max(1,p.evidence_wrong))',
    'min(.12, .015 * max(1,int(p.evidence_wrong or 0)))',
    1
)
services.write_text(s, encoding='utf-8')

main = Path('/app/app/main.py')
m = main.read_text(encoding='utf-8')
old_finish = '''@app.post("/api/practice/{session_id}/finish")
def finish_practice(session_id: str, student: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    s=session_or_404(db,session_id,student.id)
    if s.status=="finished":
        return {"session":public_session(s),"profiles":[]}
    if s.kind not in ("practice","diagnostic"): raise HTTPException(409,"Sai loại phiên")
    db.refresh(s,attribute_names=["responses"])
    correct=sum(r.correct_units for r in s.responses); total=sum(r.total_units for r in s.responses)
    s.correct_units=correct;s.total_units=total;s.score=round(10*correct/total,2) if total else 0;s.status="finished";s.finished_at=datetime.now(timezone.utc)
    chapter_scores={s.chapter:{"earned":correct,"max":total}} if s.chapter else {}
    meta=dict(s.meta_json or {});meta["chapter_scores"]=chapter_scores;s.meta_json=meta
    db.commit();db.refresh(s,attribute_names=["responses"])
    profiles=diagnostic_profiles_from_session(db,s) if s.kind=="diagnostic" else []
    return {"session":public_session(s),"profiles":profiles}'''

new_finish = '''@app.post("/api/practice/{session_id}/finish")
def finish_practice(session_id: str, student: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    s=session_or_404(db,session_id,student.id)
    if s.kind not in ("practice","diagnostic"): raise HTTPException(409,"Sai loại phiên")

    # A diagnostic session may already be marked finished if profile aggregation
    # failed after the score commit. Allow a safe one-time recovery.
    if s.status=="finished":
        meta=dict(s.meta_json or {})
        if s.kind=="diagnostic" and not meta.get("diagnostic_profile_processed"):
            db.refresh(s,attribute_names=["responses"])
            profiles=diagnostic_profiles_from_session(db,s)
            meta=dict(s.meta_json or {})
            meta["diagnostic_profile_processed"]=True
            s.meta_json=meta
            db.commit()
            return {"session":public_session(s),"profiles":profiles}
        return {"session":public_session(s),"profiles":[]}

    db.refresh(s,attribute_names=["responses"])
    correct=sum(r.correct_units for r in s.responses); total=sum(r.total_units for r in s.responses)
    s.correct_units=correct;s.total_units=total;s.score=round(10*correct/total,2) if total else 0;s.status="finished";s.finished_at=datetime.now(timezone.utc)
    chapter_scores={s.chapter:{"earned":correct,"max":total}} if s.chapter else {}
    meta=dict(s.meta_json or {});meta["chapter_scores"]=chapter_scores;s.meta_json=meta
    db.commit();db.refresh(s,attribute_names=["responses"])

    profiles=[]
    if s.kind=="diagnostic":
        profiles=diagnostic_profiles_from_session(db,s)
        meta=dict(s.meta_json or {})
        meta["diagnostic_profile_processed"]=True
        s.meta_json=meta
        db.commit()
    return {"session":public_session(s),"profiles":profiles}'''
if old_finish not in m:
    raise SystemExit('finish_practice block not found')
m = m.replace(old_finish, new_finish, 1)
main.write_text(m, encoding='utf-8')
