import inspect
import app.main as m

print("=== RELEASE INSPECT: start_practice ===")
print(inspect.getsource(m.start_practice))
print("=== RELEASE INSPECT: finish_practice ===")
print(inspect.getsource(m.finish_practice))
print("=== RELEASE INSPECT: select_practice ===")
print(inspect.getsource(m.bank.select_practice))
print("=== RELEASE INSPECT: bank selector-like methods ===")
print([name for name in dir(m.bank) if any(k in name.lower() for k in ("diagn", "select", "sample", "pick", "lesson"))])

print("=== RELEASE INSPECT: VLN-01 error ===")
print(m.bank.error_by_id.get("VLN-01"))
mapped=[q for q in m.bank.questions if "VLN-01" in str(q)]
print("=== RELEASE INSPECT: VLN-01 mapped questions ===", len(mapped))
for q in mapped[:20]:
    print({k:q.get(k) for k in ("id","chapter","lesson","type","diagnostic","errors","error_id","error_ids","misconceptions") if k in q})
    print(str(q)[:1200])
