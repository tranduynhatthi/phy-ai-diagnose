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
PY

RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/models
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
