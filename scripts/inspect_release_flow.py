import inspect
import app.main as m

print("=== RELEASE INSPECT: start_practice ===")
print(inspect.getsource(m.start_practice))
print("=== RELEASE INSPECT: finish_practice ===")
print(inspect.getsource(m.finish_practice))
print("=== RELEASE INSPECT: bank selector-like methods ===")
print([name for name in dir(m.bank) if any(k in name.lower() for k in ("diagn", "select", "sample", "pick", "lesson"))])
