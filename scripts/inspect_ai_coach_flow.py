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
