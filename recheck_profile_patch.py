from pathlib import Path

p = Path("/app/app/main.py")
text = p.read_text(encoding="utf-8")

old = '''        profiles=diagnostic_profiles_from_session(db,s)
        meta=dict(s.meta_json or {})
        meta["diagnostic_profile_processed"]=True
        s.meta_json=meta
        db.commit()'''

new = '''        profiles=diagnostic_profiles_from_session(db,s)

        # Recheck reconciliation: a repaired misconception should not remain
        # permanently flagged when a later diagnostic explicitly probes the
        # same error in a new context and the student answers those probes
        # correctly. Keep this conservative: require at least two mapped probes
        # in the current session and require all of them to be fully correct.
        repaired = db.execute(
            select(ErrorProfile).where(
                ErrorProfile.user_id == student.id,
                ErrorProfile.repair_state == "Đã sửa tốt",
            )
        ).scalars().all()
        recheck_cleared = []
        for prof in repaired:
            error_meta = bank.error_by_id.get(prof.error_id)
            if not error_meta:
                continue
            if s.chapter and error_meta.get("chapter") not in (None, s.chapter):
                continue
            if s.lesson and error_meta.get("lesson") not in (None, s.lesson):
                continue

            mapped = []
            for response in s.responses:
                q = bank.by_id.get(response.question_id)
                if q and prof.error_id in str(q):
                    mapped.append(response)

            if len(mapped) >= 2 and all(bool(r.is_fully_correct) for r in mapped):
                prev_conf = float(prof.confidence or 0.0)
                prof.confidence = round(prev_conf * 0.50, 2)
                prof.state = state_from_confidence(prof.confidence)
                prof.evidence_total = int(prof.evidence_total or 0) + len(mapped)
                prof.updated_at = datetime.now(timezone.utc)
                recheck_cleared.append(prof.error_id)

        meta=dict(s.meta_json or {})
        meta["diagnostic_profile_processed"]=True
        if recheck_cleared:
            meta["recheck_reconciled_errors"]=recheck_cleared
        s.meta_json=meta
        db.commit()'''

if old not in text:
    raise SystemExit("finish_practice diagnostic profile block not found")

p.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Recheck profile reconciliation patch applied")
