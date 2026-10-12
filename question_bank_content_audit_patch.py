"""Apply reviewed content corrections and strict answer parsing after the V3 bank."""

from pathlib import Path
import re
import sys


CONTENT_MODULE = r'''"""Validated corrections for the reviewed, immutable V3 question bank."""
import hashlib
import json
import math
import re
from pathlib import Path
from decimal import Decimal, InvalidOperation


ALLOWED_FIELDS = {"prompt", "context", "options", "answer", "explain", "statements", "tolerance", "unit"}


def canonical_digest(data):
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def rounding_places(prompt):
    match = re.search(r"(?:đến|tới)\s+(1|2|3|một|hai|ba)\s+chữ số thập phân", prompt, re.I)
    if not match:
        if re.search(r"làm tròn.{0,65}(?:hàng đơn vị|số nguyên)", prompt, re.I):
            return 0
        return None
    return {"1": 1, "2": 2, "3": 3, "một": 1, "hai": 2, "ba": 3}[match.group(1).lower()]


def numeric_choice_signature(choice):
    text = choice.strip().rstrip(".;").replace("−", "-").replace(",", ".")
    superscripts = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻", "0123456789+-")
    text = re.sub(r"10([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)", lambda m: "10^" + m.group(1).translate(superscripts), text)
    match = re.fullmatch(r"([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)(?:\s*[×·]\s*10\s*\^\s*([+-]?[0-9]+))?\s*([^0-9]*)", text)
    if not match:
        return None
    try:
        value = Decimal(match.group(1))
        if match.group(2):
            value *= Decimal(10) ** int(match.group(2))
        return value, re.sub(r"\s+", "", match.group(3))
    except (InvalidOperation, OverflowError):
        return None


def validate_questions(data):
    rows = data["questions"]
    if len(rows) != 1000 or len({q["id"] for q in rows}) != 1000:
        raise ValueError("Reviewed bank must contain 1000 distinct questions")
    for chapter, details in data["chapters"].items():
        chapter_rows = [q for q in rows if q["chapter"] == chapter]
        if len(chapter_rows) != 250 or any(q["lesson"] not in details["lessons"] for q in chapter_rows):
            raise ValueError(f"Invalid chapter or lesson distribution: {chapter}")
    for q in rows:
        if not isinstance(q.get("prompt"), str) or not q["prompt"].strip():
            raise ValueError(f"Missing question prompt: {q['id']}")
        if q["type"] == "mcq":
            options = q.get("options", [])
            if len(options) != 4 or not all(isinstance(x, str) and x.strip() for x in options):
                raise ValueError(f"Invalid choices: {q['id']}")
            if len(set(options)) != 4 or type(q.get("answer")) is not int or not 0 <= q["answer"] < 4:
                raise ValueError(f"Invalid MCQ key: {q['id']}")
            numeric = [numeric_choice_signature(option) for option in options]
            if all(item is not None for item in numeric):
                units = {unit for _, unit in numeric if unit}
                if len(units) <= 1:
                    unit = next(iter(units), "")
                    signatures = [(value, candidate_unit or unit) for value, candidate_unit in numeric]
                    if len(set(signatures)) != 4:
                        raise ValueError(f"Equivalent numeric choices: {q['id']}")
        elif q["type"] == "tf":
            statements = q.get("statements", [])
            if len(statements) != 4 or not all(type(s.get("answer")) is bool and isinstance(s.get("text"), str) and s["text"].strip() for s in statements):
                raise ValueError(f"Invalid true/false statements: {q['id']}")
        elif q["type"] == "short":
            answer, tolerance = float(q["answer"]), float(q["tolerance"])
            if not math.isfinite(answer) or not math.isfinite(tolerance) or tolerance <= 0:
                raise ValueError(f"Invalid numeric key: {q['id']}")
            places = rounding_places(q["prompt"])
            if places is not None and tolerance > 0.5 * 10 ** (-places) + 2e-12:
                raise ValueError(f"Tolerance exceeds requested decimal precision: {q['id']}")
        else:
            raise ValueError(f"Unknown question type: {q['id']}")
        for value in [q["prompt"], q.get("explain", ""), *q.get("options", []), *(s.get("text", "") for s in q.get("statements", [])), *(s.get("explain", "") for s in q.get("statements", []))]:
            if re.search(r"@@[MU]\d+@@", str(value)):
                raise ValueError(f"Renderer placeholder in question data: {q['id']}")


def apply_content_audit(data):
    audit = json.loads((Path(__file__).parent / "data/question_bank_audit.json").read_text(encoding="utf-8"))
    if audit.get("schema_version") != 1 or data.get("version") != audit["base_version"]:
        raise ValueError("Content audit does not match the bank version")
    if canonical_digest(data) != audit["baseline_sha256"]:
        raise ValueError("Content audit baseline changed; review corrections before applying")
    rows = {q["id"]: q for q in data["questions"]}
    pending = []
    seen = set()
    for correction in audit["corrections"]:
        question_id = correction["id"]
        if question_id in seen or question_id not in rows:
            raise ValueError(f"Invalid audit question ID: {question_id}")
        seen.add(question_id)
        q = rows[question_id]
        if set(correction["before"]) != set(correction["after"]) or not set(correction["after"]) <= ALLOWED_FIELDS:
            raise ValueError(f"Invalid correction fields: {question_id}")
        if any(q.get(field) != value for field, value in correction["before"].items()):
            raise ValueError(f"Question changed since content review: {question_id}")
        pending.append((q, correction["after"]))
    for q, updates in pending:
        q.update(updates)
    validate_questions(data)
    data["version"] = audit["version"]
    data.setdefault("audit", {})["content_review"] = audit["coverage"] | {"corrected_questions": len(pending)}
'''


PARSE_NUM = r'''    @staticmethod
    def _parse_num(value):
        if type(value) in (int, float):
            try:
                number = float(value)
            except (ValueError, OverflowError):
                return math.nan
        elif isinstance(value, str):
            text = value.strip().replace("−", "-").replace(",", ".")
            if not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", text):
                return math.nan
            try:
                number = float(text)
            except (ValueError, OverflowError):
                return math.nan
        else:
            return math.nan
        return number if math.isfinite(number) else math.nan
'''


MCQ_GRADE = r'''        if q["type"] == "mcq":
            try:
                if type(answer) is int:
                    index = answer
                elif type(answer) is float and math.isfinite(answer) and answer.is_integer():
                    index = int(answer)
                elif isinstance(answer, str) and re.fullmatch(r"[0-3]", answer.strip()):
                    index = int(answer.strip())
                else:
                    index = -1
                ok = index == q["answer"]
            except (ValueError, OverflowError):
                ok = False
'''


def apply_patch(root=Path("/app")):
    root = Path(root)
    audit_file = root / "app/data/question_bank_audit.json"
    if not audit_file.is_file():
        raise ValueError("Reviewed question corrections are missing from the build")
    bank_file = root / "app/question_bank.py"
    source = bank_file.read_text(encoding="utf-8")
    if "from .content_audit import apply_content_audit" not in source:
        marker = '        self.questions = questions\n'
        if source.count(marker) != 1:
            raise ValueError("Content audit: V3 validated bank marker missing")
        source = source.replace(marker, '        from .content_audit import apply_content_audit\n        apply_content_audit(self.data)\n' + marker, 1)
        source, count = re.subn(r"    @staticmethod\n    def _parse_num\(value\):.*?(?=\n    def grade\()", lambda _: PARSE_NUM, source, count=1, flags=re.S)
        if count != 1:
            raise ValueError("Content audit: numeric parser marker missing")
        source, count = re.subn(r'        if q\["type"\] == "mcq":\n            try:.*?(?=            return \{"correct_units")', lambda _: MCQ_GRADE, source, count=1, flags=re.S)
        if count != 1:
            raise ValueError("Content audit: MCQ grading marker missing")
        old = 'bool(submitted[i]) == truths[i]'
        if source.count(old) != 1:
            raise ValueError("Content audit: true/false grading marker missing")
        source = source.replace(old, 'type(submitted[i]) is bool and submitted[i] == truths[i]', 1)
    (root / "app/content_audit.py").write_text(CONTENT_MODULE, encoding="utf-8")
    bank_file.write_text(source, encoding="utf-8")
    frontend = root / "app/static/index.html"
    html = frontend.read_text(encoding="utf-8").replace('placeholder="Nhập đáp án"', 'placeholder="Nhập giá trị số, không kèm đơn vị"')
    frontend.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    apply_patch(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app"))
