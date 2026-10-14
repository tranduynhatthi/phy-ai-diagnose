import inspect
import app.main as m

for name in ["finish_practice","submit_exam","answer_practice"]:
    fn=getattr(m,name,None)
    print(f"=== {name} ===")
    print(inspect.getsource(fn) if fn else "MISSING")

print("=== LLM STATUS ===")
try:
    from app.llm_gateway import llm_gateway
    print(llm_gateway.status())
except Exception as e:
    print("LLM_STATUS_ERROR", type(e).__name__)

from pathlib import Path
html=Path("/app/app/static/index.html").read_text(encoding="utf-8")
for fn in ["submitCurrentAnswer","finishPractice","loadProfile"]:
    start=html.find("function "+fn+"(")
    if start<0:
        start=html.find("async function "+fn+"(")
    if start>=0:
        end=html.find("\nfunction ",start+1)
        async_end=html.find("\nasync function ",start+1)
        candidates=[x for x in [end,async_end] if x>=0]
        end=min(candidates) if candidates else min(len(html),start+8000)
        print(f"=== JS {fn} ===")
        print(html[start:end])
