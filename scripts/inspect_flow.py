from pathlib import Path
import json

def section(path, start, end):
    s=Path(path).read_text(encoding="utf-8",errors="ignore")
    a=s.find(start)
    b=s.find(end,a+len(start)) if a>=0 else -1
    if a<0:
        print(f"NOT_FOUND {path} :: {start}")
        return
    if b<0:
        b=min(len(s),a+16000)
    print(f"=== {path} :: {start} ===")
    print(s[a:b])

section("app/main.py",'def answer_practice','@app.post("/api/practice/{session_id}/finish")')
section("app/services.py",'def diagnostic_profiles_from_session','def recent_performance')
section("app/services.py",'def build_repair','def grade_repair_item')
section("app/services.py",'def grade_repair_item','def ')

from app.main import bank
print("=== EFFECTIVE VLN-01 ERROR ===")
print(json.dumps(bank.error_by_id.get("VLN-01"),ensure_ascii=False,indent=2))
print("=== EFFECTIVE QUESTIONS TAGGED VLN-01 ===")
for q in bank.questions:
    if "VLN-01" in json.dumps(q,ensure_ascii=False):
        print(json.dumps(q,ensure_ascii=False,indent=2))
