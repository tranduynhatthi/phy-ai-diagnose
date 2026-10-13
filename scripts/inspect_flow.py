from pathlib import Path

def show(path: str, needle: str, before: int = 20, after: int = 140):
    p = Path(path)
    if not p.exists():
        print(f"MISSING {path}")
        return
    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    for i, line in enumerate(lines):
        if needle in line:
            a=max(0,i-before); b=min(len(lines),i+after+1)
            print(f"=== {path} :: {needle} :: lines {a+1}-{b} ===")
            for j in range(a,b):
                print(f"{j+1}: {lines[j]}")
            return
    print(f"NOT_FOUND {path} :: {needle}")

show("app/main.py","def answer_practice")
show("app/main.py","def start_repair")
show("app/main.py","def answer_repair")
show("app/main.py","def finish_repair")
show("app/services.py","def finish_diagnostic",30,220)
show("app/services.py","def finish_repair",30,220)
show("app/question_bank.py","def",5,20)

for p in [Path("app/data/question_bank.json"), Path("app/data/error_library.json")]:
    if p.exists():
        text=p.read_text(encoding="utf-8",errors="ignore")
        idx=text.find("VLN-01")
        if idx>=0:
            print(f"=== {p} :: VLN-01 ===")
            print(text[max(0,idx-3000):idx+7000])
