"""Save teacher workspace before student-only presentation strips its markup.

The source is the already assembled educator/admin dashboard, not a handwritten
replacement. This keeps existing classroom controls and identifiers unchanged.
"""
from pathlib import Path
import json
import re

html=Path("/app/app/static/index.html").read_text(encoding="utf-8")
snippets={}
patterns={
    "teacher_login":r'<article class="portal-card teacher-portal"[\s\S]*?</article>',
    "teacher_workspace":r'<section id="teacherView"[^>]*>[\s\S]*?</section>',
}
for name,pattern in patterns.items():
    found=re.findall(pattern,html)
    if len(found)!=1:raise SystemExit(f"Expected one educator section: {name}, got {len(found)}")
    snippets[name]=found[0]
Path("/tmp/teacher_portal_snapshot.json").write_text(
    json.dumps(snippets,ensure_ascii=False),encoding="utf-8")
print("Educator login card and dashboard preserved for subsequent public UI restoration")
