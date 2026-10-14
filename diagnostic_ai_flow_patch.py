from pathlib import Path
import re

p = Path("/app/app/main.py")
text = p.read_text(encoding="utf-8")

if "from .llm_gateway import llm_gateway" not in text:
    # Insert beside application-local imports.
    anchor = "from ."
    pos = text.find(anchor)
    if pos < 0:
        raise SystemExit("Could not locate local imports in app/main.py")
    text = text[:pos] + "from .llm_gateway import llm_gateway\n" + text[pos:]

pattern = re.compile(
    r'@app\.post\("/api/practice/\{session_id\}/answer"\)\n'
    r'def answer_practice\(.*?\n'
    r'(?=@app\.post\("/api/practice/\{session_id\}/finish"\))',
    re.S,
)

replacement = '''@app.post("/api/practice/{session_id}/answer")
def answer_practice(session_id:str, req:AnswerRequest, student:User=Depends(require_roles("student")), db:Session=Depends(get_db)):
    s=session_or_404(db,session_id,student.id)
    if s.kind not in {"practice","diagnostic"} or s.status!="active":
        raise HTTPException(409,"Phiên luyện tập/chẩn đoán không hoạt động")
    if not isinstance(req.answer,dict) or "question_id" not in req.answer:
        raise HTTPException(400,"Thiếu question_id")
    qid=str(req.answer["question_id"]); value=req.answer.get("value")
    qids=(s.meta_json or {}).get("question_ids",[])
    if qid not in qids:
        raise HTTPException(400,"Câu hỏi không thuộc phiên")
    if db.execute(select(Response).where(Response.session_id==s.id,Response.question_id==qid)).scalar_one_or_none():
        raise HTTPException(409,"Câu hỏi đã được trả lời")

    q=bank.by_id[qid]
    grade=bank.grade(q,value)

    reasoning=(req.reasoning or "").strip()
    answer_payload={"value":value}
    if reasoning:
        answer_payload["reasoning"]=reasoning

    ai_analysis={"used":False,"reason":"no_reasoning","candidate_errors":[],"feedback":""}
    if s.kind=="diagnostic" and reasoning:
        ai_analysis=llm_gateway.analyze_reasoning(
            question=q,
            student_answer=value,
            reasoning=reasoning,
            valid_errors=list(bank.error_by_id.values()),
            user_id=str(student.id),
        )
        # Persist both successful and fallback results for auditability.
        answer_payload["ai_analysis"]=ai_analysis

    db.add(Response(
        session_id=s.id,
        question_id=qid,
        answer_json=answer_payload,
        correct_units=grade["correct_units"],
        total_units=grade["total_units"],
        is_fully_correct=grade["is_fully_correct"],
        duration_ms=req.duration_ms,
    ))
    db.commit()

    if s.kind=="practice":
        return {
            "recorded":True,
            "correct":grade["is_fully_correct"],
            "correct_units":grade["correct_units"],
            "total_units":grade["total_units"],
            "correct_answer":grade.get("correct_answer"),
            "unit":grade.get("unit",""),
            "explain":grade.get("explain",""),
        }
    return {"recorded":True,"ai":ai_analysis if reasoning else None}

'''

new_text, n = pattern.subn(replacement, text, count=1)
if n != 1:
    raise SystemExit(f"Could not replace answer_practice safely; matches={n}")

p.write_text(new_text, encoding="utf-8")
print("Diagnostic Gemini answer-flow patch applied")
