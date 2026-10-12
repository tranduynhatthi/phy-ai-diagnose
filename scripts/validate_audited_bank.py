"""Check the effective bank, including the V3 and content audit patches."""

import json
import argparse
import os
from pathlib import Path
import sys

root = os.environ.get("PHY_APP_ROOT", "/app")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--export", type=Path, help="Write the effective reviewed bank for browser checks")
args = parser.parse_args()
if not (Path(root) / "app/question_bank.py").is_file():
    raise SystemExit("Set PHY_APP_ROOT to the Docker-assembled application directory")
sys.path.insert(0, str(Path(root).resolve()))

from app.question_bank import bank
from app.content_audit import validate_questions

validate_questions(bank.data)
review = bank.data["audit"]["content_review"]
assert review["reviewed_questions"] == 1000
assert review["reviewed_tf_statements"] == 872
assert review["recomputed_short_answers"] == 250
if args.export:
    args.export.parent.mkdir(parents=True, exist_ok=True)
    args.export.write_text(json.dumps(bank.data, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"version": bank.data["version"], "questions": len(bank.questions), "review": review, "issues": []}, ensure_ascii=False, indent=2))
