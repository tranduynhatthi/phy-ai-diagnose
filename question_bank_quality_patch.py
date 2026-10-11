from pathlib import Path

p=Path('/app/app/question_bank.py')
s=p.read_text(encoding='utf-8')

s=s.replace(
    'import json, math, random, re',
    'import json, math, random, re, os, base64, gzip, hashlib',
    1
)

old='''        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.questions = self.data["questions"]'''
new='''        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        patch_parts = sorted(Path("/app/v3_patch").glob("part*.b64"))
        if patch_parts:
            patch_b64 = "".join(p.read_text(encoding="utf-8").strip() for p in patch_parts)
        else:
            patch_b64 = "".join(os.getenv(f"QUESTION_PATCH_{i}", "") for i in range(16))
        if patch_b64:
            if len(patch_b64) != 78124:
                raise RuntimeError(f"Gói V3 sai độ dài: {len(patch_b64)}/78124")
            digest = hashlib.sha256(patch_b64.encode("ascii")).hexdigest()
            if digest != "988a441a3afc49d4d6ee2feb1f59376b3db4e0f337dcb155bc29093d00568f09":
                raise RuntimeError("Gói V3 không khớp checksum đã hậu kiểm")
            try:
                payload = json.loads(gzip.decompress(base64.b64decode(patch_b64)).decode("utf-8"))
            except Exception as exc:
                raise RuntimeError("Không đọc được gói hậu kiểm ngân hàng câu hỏi V3") from exc
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

        questions = self.data.get("questions", [])
        if self.data.get("version") != "2026.10-1000q-quality-v3-senior-physics-audit":
            raise RuntimeError(f"Phiên bản ngân hàng không đúng V3: {self.data.get('version')}")
        if len(questions) != 1000:
            raise RuntimeError(f"Ngân hàng V3 phải có 1000 câu, hiện có {len(questions)}")
        chapter_counts = {}
        type_counts = {}
        for q in questions:
            chapter_counts[q.get("chapter")] = chapter_counts.get(q.get("chapter"), 0) + 1
            type_counts[q.get("type")] = type_counts.get(q.get("type"), 0) + 1
        if len(chapter_counts) != 4 or sorted(chapter_counts.values()) != [250, 250, 250, 250]:
            raise RuntimeError(f"Phân bố chương V3 không hợp lệ: {chapter_counts}")
        expected_types = {"mcq": 532, "tf": 218, "short": 250}
        if type_counts != expected_types:
            raise RuntimeError(f"Phân bố dạng câu V3 không hợp lệ: {type_counts}")
        print(f"[QUESTION_BANK_V3] version={self.data.get('version')} total={len(questions)} chapters={chapter_counts} types={type_counts}", flush=True)
        self.questions = questions'''
if old not in s:
    raise SystemExit('question bank load marker not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
