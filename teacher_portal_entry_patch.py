"""Expose a safe, obvious teacher/admin login entry point to student-signed-in visitors.
No role elevation; going to teacher portal logs out the current student session.
"""
from pathlib import Path
import re

ROOT=Path("/app/app/static/index.html")
html=ROOT.read_text(encoding="utf-8")
if 'id="teacherAccountSwitch"' in html:
    raise SystemExit("Teacher account switch already installed")
if 'id="teacherLoginForm"' not in html or 'id="adminView"' not in html:
    raise SystemExit("Expected separate teacher/auth/admin views are missing")
match=re.search(r'<section\s+id="studentView"[^>]*>',html)
if not match:
    raise SystemExit("Student workspace marker missing")
switch=r'''
<div id="teacherAccountSwitch" class="teacher-account-switch" role="navigation" aria-label="Chuyển không gian tài khoản">
 <div>
  <strong>Đăng nhập nhầm không gian?</strong>
  <span>Quản trị viên và Giáo viên dùng cổng Giáo viên, không dùng tài khoản Học sinh.</span>
 </div>
 <a class="btn secondary" href="/?portal=teacher" id="goTeacherPortal">Đến cổng Giáo viên / Quản trị viên →</a>
</div>
'''
html=html[:match.end()]+"\n"+switch+html[match.end():]
css=r'''
<style id="teacher-account-switch-styles">
.teacher-account-switch{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;margin:0 0 18px;padding:14px 16px;border:1px solid #d6e5f4;border-radius:14px;background:#f4f8fd;color:#173a62}
.teacher-account-switch strong{display:block;font-size:14px;margin:0 0 4px}
.teacher-account-switch span{display:block;font-size:12px;line-height:1.5}
.teacher-account-switch a{white-space:normal;text-align:center}
@media(max-width:620px){.teacher-account-switch{align-items:stretch}.teacher-account-switch a{width:100%}}
</style>
'''
if "</head>" not in html: raise SystemExit("HTML head closure missing")
html=html.replace("</head>",css+"</head>",1)
old="""async function boot(){
 const restoreToken=token;"""
new="""async function boot(){
 // Explicit teacher entry is a one-time account switch, never a privilege change.
 if(new URLSearchParams(window.location.search).get('portal')==='teacher'){
  window.history.replaceState(null,'',window.location.pathname);
  if(token)logout();
  else show('authView');
  const teacherLogin=document.getElementById('teacherLoginUser');
  if(teacherLogin)teacherLogin.focus();
  return;
 }
 const restoreToken=token;"""
if html.count(old)!=1:
    raise SystemExit("Expected one boot() restoration block for teacher portal deep link")
html=html.replace(old,new,1)
ROOT.write_text(html,encoding="utf-8")
print("Teacher portal deep link and student account switch are installed.")
