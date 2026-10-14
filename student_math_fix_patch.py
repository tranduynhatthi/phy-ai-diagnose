from pathlib import Path
p=Path('/app/app/static/index.html')
s=p.read_text(encoding='utf-8')
s=s.replace('esc(x.question.prompt)','mathHtml(x.question.prompt)')
p.write_text(s,encoding='utf-8')
