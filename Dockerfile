FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY deploy_bundle /tmp/deploy_bundle
RUN python - <<'PY'
from pathlib import Path
import base64, zipfile, shutil

parts = sorted(Path('/tmp/deploy_bundle').glob('part*.b64'))
if not parts:
    raise SystemExit('deployment bundle missing')

payload = ''.join(p.read_text(encoding='utf-8').strip() for p in parts)
archive = Path('/tmp/phy_ai.zip')
archive.write_bytes(base64.b64decode(payload))

with zipfile.ZipFile(archive) as z:
    z.extractall('/tmp/src')

source = Path('/tmp/src/PHY_AI_DIAGNOSE_PRODUCTION_SERVER')
if not source.exists():
    raise SystemExit('production source directory missing from archive')

shutil.copytree(source, Path('/app'), dirs_exist_ok=True)

frontend = Path('/app/app/static/index.html')
html = frontend.read_text(encoding='utf-8')

# Browser fix: window.top is a reserved browser global.
html = html.replace('function top(){', 'function renderTop(){')
html = html.replace('top();', 'renderTop();')

# Make validation errors readable and normalize registration input.
html = html.replace(
    "if(!r.ok)throw new Error(data.detail||'Có lỗi xảy ra');return data",
    "if(!r.ok){let d=data.detail;if(Array.isArray(d))d=d.map(x=>x.msg||String(x)).join(' · ');throw new Error(d||'Có lỗi xảy ra')}return data"
)
html = html.replace(
    "display_name:$('regName').value,username:$('regUser').value,password:$('regPass').value",
    "display_name:$('regName').value.trim(),username:$('regUser').value.trim().toLowerCase(),password:$('regPass').value"
)
html = html.replace(
    '<input id="regUser" placeholder="vd: 12a1-nguyenvana"></div>',
    '<input id="regUser" placeholder="vd: 12a1-nguyenvana"><div class="small muted">Tối thiểu 3 kí tự; chỉ dùng a-z, 0-9, dấu chấm, gạch dưới hoặc gạch ngang.</div></div>'
)
html = html.replace(
    '<input id="regPass" type="password"></div>',
    '<input id="regPass" type="password"><div class="small muted">Mật khẩu tối thiểu 8 kí tự.</div></div>'
)

frontend.write_text(html, encoding='utf-8')
PY

RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/models
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
