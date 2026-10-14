from pathlib import Path

p = Path("/app/app/services.py")
text = p.read_text(encoding="utf-8")

replacements = {
    'ok = int(answer) == int(item["answer"]) if str(answer).strip() != "" else False':
        'ok = int(answer) == int(item["answer"]) if answer is not None and str(answer).strip() != "" else False',
    'ok = abs(float(answer)-float(item["answer"])) <= float(item.get("tolerance",0.01)) if str(answer).strip() != "" else False':
        'ok = abs(float(answer)-float(item["answer"])) <= float(item.get("tolerance",0.01)) if answer is not None and str(answer).strip() != "" else False',
}
changed = 0
for old, new in replacements.items():
    if old in text:
        text = text.replace(old, new)
        changed += 1

if changed == 0:
    raise SystemExit("Repair null-answer guard: expected grading expression not found")

p.write_text(text, encoding="utf-8")
print(f"Repair null-answer guard applied ({changed} expression(s))")
