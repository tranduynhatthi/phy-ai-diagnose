from pathlib import Path
import re

p = Path('/app/app/static/index.html')
html = p.read_text(encoding='utf-8')

# Remove the verbose role-comparison section ("Hai không gian làm việc...").
needle = 'Hai không gian làm việc, một hệ thống dữ liệu'
idx = html.find(needle)
if idx != -1:
    start = html.rfind('<section', 0, idx)
    end = html.find('</section>', idx)
    if start != -1 and end != -1:
        html = html[:start] + html[end + len('</section>'):]

# Remove the long explanatory paragraph beginning with "PHY-AI DIAGNOSE giúp học sinh...".
html = re.sub(
    r'<p\b[^>]*>\s*PHY-AI DIAGNOSE giúp học sinh.*?dashboard thống nhất\.\s*</p>',
    '',
    html,
    count=1,
    flags=re.S
)

# Also remove a possible div wrapper containing only that same sentence.
html = re.sub(
    r'<div\b[^>]*>\s*PHY-AI DIAGNOSE giúp học sinh.*?dashboard thống nhất\.\s*</div>',
    '',
    html,
    count=1,
    flags=re.S
)

p.write_text(html, encoding='utf-8')
