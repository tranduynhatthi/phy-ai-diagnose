import inspect
import re
import app.main as m

for name in ("start_practice","finish_practice","start_repair","profile"):
    fn=getattr(m,name,None)
    print(f"=== RELEASE INSPECT: {name} ===")
    print(inspect.getsource(fn) if fn else "MISSING")

print("=== RELEASE INSPECT: select_practice ===")
print(inspect.getsource(m.bank.select_practice))

print("=== RELEASE INSPECT: PROMPT FORMULA CANDIDATES ===")
formula_terms=(
    "công thức","hệ thức","biểu thức","theo định luật","áp dụng định luật",
    "pV","V/T","p/T","Q =","Q=","ΔU","lambda","λ","Phi","Φ",
    "e_c","U_1","U1/U2","N_1","N1/N2","E = mc","E=mc",
    "N_t","Nₜ","H_t","Hₜ","I =","I=","U =","U=",
)
seen=[]
for q in m.bank.questions:
    prompt=str(q.get("prompt") or "")
    if "=" in prompt or any(t.lower() in prompt.lower() for t in formula_terms):
        seen.append((q.get("id"),q.get("chapter"),q.get("lesson"),q.get("type"),prompt))
print("FORMULA_CANDIDATE_COUNT",len(seen))
for row in seen:
    print("FORMULA_CANDIDATE|"+ "|".join(str(x).replace("\n"," ") for x in row))

print("=== RELEASE INSPECT: TEXTAREA / TEACHER MARKERS ===")
html=(m.STATIC_DIR/"index.html").read_text(encoding="utf-8") if hasattr(m,"STATIC_DIR") else ""
for term in ['id="qReasoning"','teacher-portal','id="teacherView"','resultProfiles']:
    print(term, html.find(term))
