"""Restore real teacher and admin portals safely after v1.4's student-only UI patch.

The teacher DOM is snapshotted from the original fully assembled v1.3 pages before
student_selfstudy_patch removes it; backend and student self-study are untouched.
"""
from pathlib import Path
import json
import re

file=Path("/app/app/static/index.html")
html=file.read_text(encoding="utf-8")
archive=Path("/tmp/teacher_portal_snapshot.json")
if not archive.is_file():
    raise SystemExit("Missing pre-selfstudy educator UI snapshot")
snapshot=json.loads(archive.read_text(encoding="utf-8"))

if 'id="teacherLoginForm"' in html or 'id="teacherView"' in html:
    raise SystemExit("Teacher portal already exists; refuse duplicate restoration")
marker='<article class="portal-card student-portal"'
if html.count(marker)!=1:raise SystemExit("Student login card missing or duplicated")
html=html.replace(marker,snapshot["teacher_login"]+"\n  "+marker,1)
if html.count("</main>")!=1:raise SystemExit("Missing unique main closure")
html=html.replace("</main>",snapshot["teacher_workspace"]+"\n</main>",1)

# The student-only conversion removed the teacher form from its UI helpers.
# Restore secure cleanup on logout (including password fields) and busy state.
replacements={
 "for(const id of ['studentLoginSubmit','studentRegisterSubmit']){const el=$(id);if(el)el.disabled=busy;}":
 "for(const id of ['teacherLoginSubmit','studentLoginSubmit','studentRegisterSubmit']){const el=$(id);if(el)el.disabled=busy;}",
 "for(const id of ['studentLoginForm','studentRegisterForm']){const el=$(id);if(el)el.reset();}":
 "for(const id of ['teacherLoginForm','studentLoginForm','studentRegisterForm']){const el=$(id);if(el)el.reset();}",
 "for(const id of ['studentLoginMsg','regMsg']){const el=$(id);if(el)el.textContent='';}":
 "for(const id of ['teacherLoginMsg','studentLoginMsg','regMsg']){const el=$(id);if(el)el.textContent='';}",
 "if($('studentLoginMsg'))$('studentLoginMsg').textContent='Không kết nối được máy chủ. Vui lòng thử đăng nhập lại.';":
 "for(const id of ['teacherLoginMsg','studentLoginMsg']){const el=$(id);if(el)el.textContent='Không kết nối được máy chủ. Vui lòng thử đăng nhập lại.';}",
}
for old,new in replacements.items():
    if html.count(old)!=1:raise SystemExit("Auth helper not found exactly once: "+old[:65])
    html=html.replace(old,new,1)

route=re.compile(r'^function routeHome\(classes=\[\]\)\{[^\n]*\}\n',re.M)
new_route="""function routeHome(classes=[]){
 if(!me){show('authView');return}
 if(me.role==='student'){initStudent(classes);show('studentView');loadProfile()}
 else if(me.role==='admin'){show('adminView');loadAdminUsers(true)}
 else if(me.role==='teacher'){show('teacherView');loadTeacher()}
 else{logout()}
}
"""
html,count=route.subn(lambda _:new_route,html,count=1)
if count!=1:raise SystemExit("Could not restore role-aware dashboard routing")

logout=re.compile(r'^function logout\(\)\{[^\n]*\}\n',re.M)
new_logout="""function logout(){
 token='';me=null;currentClassId=null;currentStudentId=null;
 teacherLoadVersion++;classRequestVersion++;studentRequestVersion++;schoolRequestVersion++;
 currentSchoolId=null;teacherSchools=[];currentSchoolCode='';
 if($('schoolDetailCard'))$('schoolDetailCard').classList.add('hidden');
 if($('studentDetailCard'))$('studentDetailCard').classList.add('hidden');
 if($('exportBtn'))$('exportBtn').classList.add('hidden');
 if(examTimerHandle){clearInterval(examTimerHandle);examTimerHandle=null}
 localStorage.removeItem('phy_token');clearAuthForms();
 if(typeof clearAdminState==='function')clearAdminState();
 show('authView');renderTop();
}
"""
html,count=logout.subn(lambda _:new_logout,html,count=1)
if count!=1:raise SystemExit("Logout reinitialization marker missing")

# Self-study intro is retained for pupils while teachers now get their own card.
html=html.replace("Tự học Vật lí 12 theo lỗi sai của chính em",
                  "Tự học Vật lí 12 và quản lý lớp học",1)
html=html.replace("Dành cho học sinh trung bình và yếu: làm bài, biết mình sai ở đâu, sửa đúng lỗi rồi kiểm tra lại bằng ngữ cảnh mới.",
                  "Chọn cổng Giáo viên để quản lý lớp hoặc cổng Học sinh để chẩn đoán và sửa lỗi tư duy.",1)

match=re.search(r'<section\s+id="studentView"[^>]*>',html)
if not match:raise SystemExit("Student workspace marker missing")
switch=r'''
<div id="teacherAccountSwitch" class="teacher-account-switch" role="navigation" aria-label="Chuyển không gian tài khoản">
 <div>
  <strong>Bạn cần vào tài khoản Giáo viên hoặc Quản trị viên?</strong>
  <span>Đăng xuất khỏi tài khoản Học sinh để đăng nhập bằng tài khoản được cấp quyền.</span>
 </div>
 <a class="btn secondary" href="/?portal=teacher" id="goTeacherPortal">Đến cổng Giáo viên / Quản trị viên →</a>
</div>
'''
html=html[:match.end()]+"\n"+switch+html[match.end():]
css=r'''
<style id="teacher-account-switch-styles">
#authView.auth{max-width:1040px}
#authView .portal-grid{grid-template-columns:repeat(2,minmax(0,1fr));max-width:none}
.teacher-account-switch{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;margin:0 0 18px;padding:14px 16px;border:1px solid #d6e5f4;border-radius:14px;background:#f4f8fd;color:#173a62}
.teacher-account-switch strong{display:block;font-size:14px;margin:0 0 4px}
.teacher-account-switch span{display:block;font-size:12px;line-height:1.5}
.teacher-account-switch a{white-space:normal;text-align:center}
@media(max-width:680px){#authView .portal-grid{grid-template-columns:1fr}.teacher-account-switch{align-items:stretch}.teacher-account-switch a{width:100%}}
</style>
'''
if "</head>" not in html:raise SystemExit("Missing HTML head")
html=html.replace("</head>",css+"</head>",1)
old="""async function boot(){
 const restoreToken=token;"""
new="""async function boot(){
 // A direct teacher login link revokes the old local login; permissions
 // still come only from the backend after fresh teacher/admin authentication.
 if(new URLSearchParams(window.location.search).get('portal')==='teacher'){
  window.history.replaceState(null,'',window.location.pathname);
  if(token)logout();
  else show('authView');
  const teacherLogin=document.getElementById('teacherLoginUser');
  if(teacherLogin)teacherLogin.focus();
  return;
 }
 const restoreToken=token;"""
if html.count(old)!=1:raise SystemExit("Expected one boot() marker")
html=html.replace(old,new,1)
for ref in ('id="teacherLoginForm"','id="teacherView"','id="adminView"','id="questionAdminRoot"','id="teacherAccountSwitch"'):
    if html.count(ref)!=1:raise SystemExit("Missing or repeated role element: "+ref)
file.write_text(html,encoding="utf-8")
print("Full teacher and admin screens restored; self-study preserved.")
