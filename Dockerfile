FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY deploy_bundle /tmp/deploy_bundle
COPY answer_flow_patch.py /tmp/answer_flow_patch.py
COPY math_patch.py /tmp/math_patch.py
COPY math_render_fix_v2.py /tmp/math_render_fix_v2.py
COPY teacher_patch.py /tmp/teacher_patch.py
COPY teacher_dashboard_v2.py /tmp/teacher_dashboard_v2.py
COPY admin_patch.py /tmp/admin_patch.py
COPY admin_bootstrap_patch.py /tmp/admin_bootstrap_patch.py
COPY admin_password_patch.py /tmp/admin_password_patch.py
COPY question_bank_quality_patch.py /tmp/question_bank_quality_patch.py
COPY question_bank_content_audit_patch.py /tmp/question_bank_content_audit_patch.py
COPY question_bank_audit.json /app/app/data/question_bank_audit.json
COPY diagnostic_finish_fix.py /tmp/diagnostic_finish_fix.py
COPY multi_school_home_patch.py /tmp/multi_school_home_patch.py
COPY homepage_cleanup_patch.py /tmp/homepage_cleanup_patch.py
COPY role_access_patch.py /tmp/role_access_patch.py
COPY role_portal_patch.py /tmp/role_portal_patch.py
COPY admin_accounts_patch.py /tmp/admin_accounts_patch.py
COPY latex_standard_patch.py /tmp/latex_standard_patch.py
COPY hybrid_patch /tmp/hybrid_patch
COPY v3_patch /app/v3_patch
RUN python - <<'PY'
from pathlib import Path
import base64, zipfile, shutil, re

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
html = html.replace('top()', 'renderTop()')

# Make authentication and validation errors accurate and readable.
html = html.replace(
    "async function api(path,opt={}){opt.headers=Object.assign({'Content-Type':'application/json'},opt.headers||{});if(token)opt.headers.Authorization='Bearer '+token;const r=await fetch(path,opt);if(r.status===401){logout();throw new Error('Phiên đăng nhập đã hết hạn')}let data;try{data=await r.json()}catch(e){data={detail:'Lỗi máy chủ'}}if(!r.ok)throw new Error(data.detail||'Có lỗi xảy ra');return data}",
    "async function api(path,opt={}){opt.headers=Object.assign({'Content-Type':'application/json'},opt.headers||{});if(token&&!path.startsWith('/api/auth/'))opt.headers.Authorization='Bearer '+token;const r=await fetch(path,opt);let data;try{data=await r.json()}catch(e){data={detail:'Lỗi máy chủ'}}if(r.status===401){if(path==='/api/auth/login')throw new Error(data.detail||'Tên đăng nhập hoặc mật khẩu không đúng');logout();throw new Error(data.detail||'Phiên đăng nhập đã hết hạn')}if(!r.ok){let d=data.detail;if(Array.isArray(d))d=d.map(x=>x.msg||String(x)).join(' · ');throw new Error(d||'Có lỗi xảy ra')}return data}"
)
html = html.replace(
    "username:$('loginUser').value,password:$('loginPass').value",
    "username:$('loginUser').value.trim().toLowerCase(),password:$('loginPass').value"
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

# Remove the unvalidated/fake-looking ability summary from the student UI.
html = html.replace(
    '<div class="toolbar"><h2>Đề luyện cuối năm</h2><button class="btn ghost" onclick="loadProfile()">Cập nhật</button></div>\n   <div id="abilityBox"></div>',
    '<h2>Đề luyện cuối năm</h2>'
)
html = html.replace(
    '<div class="field"><label>Mức đề</label><select id="examLevel"><option value="auto">Tự động</option><option value="foundation">Củng cố nền tảng</option><option value="developing">Đang phát triển</option><option value="proficient">Khá – vững</option><option value="advanced">Nâng cao</option><option value="balanced">Cân bằng</option></select></div>',
    '<div class="field"><label>Mức đề</label><select id="examLevel"><option value="balanced" selected>Cân bằng</option><option value="foundation">Củng cố nền tảng</option><option value="developing">Đang phát triển</option><option value="proficient">Khá – vững</option><option value="advanced">Nâng cao</option></select></div>'
)
html = re.sub(
    r"let p=await api\('/api/profile'\);let a=p\.ability;\$\('abilityBox'\)\.innerHTML=\`.*?\`;\$\('errorProfile'\)",
    "let p=await api('/api/profile');$('errorProfile')",
    html,
    count=1
)

frontend.write_text(html, encoding='utf-8')
PY

RUN python /tmp/answer_flow_patch.py
RUN python /tmp/math_patch.py
RUN python /tmp/math_render_fix_v2.py
RUN python /tmp/teacher_patch.py
RUN python /tmp/teacher_dashboard_v2.py
RUN python /tmp/admin_patch.py
RUN python /tmp/admin_bootstrap_patch.py
RUN python /tmp/admin_password_patch.py
RUN python /tmp/question_bank_quality_patch.py
RUN python /tmp/question_bank_content_audit_patch.py
RUN python /tmp/diagnostic_finish_fix.py
RUN python /tmp/multi_school_home_patch.py
RUN python /tmp/homepage_cleanup_patch.py
RUN python /tmp/role_access_patch.py
RUN python /tmp/role_portal_patch.py
RUN python /tmp/admin_accounts_patch.py
RUN python /tmp/latex_standard_patch.py
RUN cat /tmp/hybrid_patch/part*.b64 | base64 -d | gzip -d > /tmp/hybrid_ai_patch.py && python /tmp/hybrid_ai_patch.py

RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/models
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
