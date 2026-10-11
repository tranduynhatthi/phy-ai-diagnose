from pathlib import Path

p=Path('/app/app/question_bank.py')
s=p.read_text(encoding='utf-8')

s=s.replace(
    'import json, math, random, re',
    'import json, math, random, re, os, base64, gzip',
    1
)

old='''        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.questions = self.data["questions"]'''
new='''        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        patch_b64 = "".join(os.getenv(f"QUESTION_PATCH_{i}", "") for i in range(4))
        if patch_b64:
            try:
                payload = json.loads(gzip.decompress(base64.b64decode(patch_b64)).decode("utf-8"))
            except Exception as exc:
                raise RuntimeError("Không đọc được gói hậu kiểm ngân hàng câu hỏi") from exc
            delta = payload.get("patch", {})
            if len(delta) != 619:
                raise RuntimeError(f"Gói hậu kiểm câu hỏi không đầy đủ: {len(delta)}/619")
            rows = {q.get("id"): q for q in self.data.get("questions", [])}
            missing = [qid for qid in delta if qid not in rows]
            if missing:
                raise RuntimeError(f"Không tìm thấy {len(missing)} câu cần hậu kiểm trong ngân hàng gốc")
            for qid, fields in delta.items():
                rows[qid].update(fields)
            self.data["version"] = payload.get("version", self.data.get("version"))
            self.data["audit"] = payload.get("audit", self.data.get("audit", {}))
        self.questions = self.data["questions"]'''
if old not in s:
    raise SystemExit('question bank load marker not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
