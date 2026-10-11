"""Add separate teacher and student entry points to the packaged web app."""
from pathlib import Path
import re
import sys


PORTAL_CSS = """
<style id="role-portal-styles">
#authView.auth{max-width:1040px;margin:28px auto}
.portal-intro{text-align:center;max-width:620px;margin:0 auto 28px}
.portal-intro .pill{letter-spacing:.08em}
.portal-intro h1{font-size:clamp(26px,4vw,38px);line-height:1.2;letter-spacing:-.035em;margin:14px 0 12px}
.portal-intro p{line-height:1.65;margin:0;color:var(--muted)}
.portal-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px;align-items:start}
.portal-card{--accent:#2457a7;--accent-dark:#1e478a;--tint:#edf3fd;--border:#d9e5f7;background:#fff;border:1px solid var(--border);border-top:4px solid var(--accent);border-radius:20px;padding:28px;box-shadow:0 12px 32px rgba(47,36,30,.05)}
.portal-card.student-portal{--accent:#c7510d;--accent-dark:#a43e09;--tint:#fff2e8;--border:#f4dac7}
.portal-heading{display:flex;gap:16px;align-items:center;margin-bottom:16px}
.portal-icon{width:54px;height:54px;flex-shrink:0;border-radius:16px;display:grid;place-items:center;background:var(--tint);color:var(--accent)}
.portal-icon svg{width:28px;height:28px}
.portal-eyebrow{font-size:10px;font-weight:800;letter-spacing:.1em;color:var(--accent);margin:0 0 5px}
.portal-heading h2{font-size:26px;letter-spacing:-.025em;margin:0}
.portal-description{color:var(--muted);font-size:14px;line-height:1.65;margin:0 0 16px;min-height:46px}
.portal-features{display:flex;flex-wrap:wrap;gap:8px;list-style:none;margin:0 0 22px;padding:0}
.portal-features li{font-size:11px;font-weight:700;color:var(--accent);background:var(--tint);padding:7px 9px;border-radius:8px}
.portal-form{border-top:1px solid var(--border);padding-top:6px}
.portal-card .field{margin:16px 0}
.portal-card .field label{color:var(--text);font-size:13px}
.portal-card input{border-radius:10px;padding:12px 13px;min-width:0}
.portal-card input:focus-visible{outline:3px solid var(--tint);border-color:var(--accent)}
.portal-submit{width:100%;background:var(--accent);color:#fff;min-height:46px;margin-top:6px}
.portal-submit:hover{background:var(--accent-dark)}
.portal-card button:focus-visible,.portal-registration summary:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
.portal-submit:disabled{opacity:.65;cursor:wait}
.portal-message{color:var(--bad);font-size:13px;line-height:1.5;min-height:20px;margin:10px 0 0}
.portal-note{border-top:1px solid var(--border);margin:16px 0 0;padding-top:16px;font-size:12px;line-height:1.65;color:var(--muted)}
.portal-registration{border-top:1px solid var(--border);margin-top:16px;padding-top:16px}
.portal-registration summary{cursor:pointer;font-size:13px;font-weight:700;color:var(--accent);line-height:1.6}
.portal-registration .registration-hint{font-size:12px;line-height:1.6;color:var(--muted);margin:12px 0}
#teacherView .secondary{background:#edf3fd;color:#2457a7;border-color:#cadbf5}
#teacherView .pill{background:#edf3fd;color:#2457a7}
#teacherView .stat{background:#f3f7fd;border-color:#d9e5f7}
#teacherView .stat b{color:#2457a7}
#teacherView .teacher-intro{line-height:1.6;margin-bottom:20px}
@media(max-width:680px){#authView.auth{margin:16px auto}.portal-grid{grid-template-columns:1fr;gap:18px}.portal-card{padding:22px}.portal-intro{margin-bottom:22px}.portal-description{min-height:0}}
@media(prefers-reduced-motion:no-preference){.portal-submit{transition:background .15s}}
</style>
"""

AUTH_SECTION = """
<section id="authView" class="auth" aria-labelledby="portalTitle">
 <div class="portal-intro">
  <span class="pill">VẬT LÍ 12</span>
  <h1 id="portalTitle">Chọn không gian của bạn</h1>
  <p>Đăng nhập để tiếp tục học tập hoặc quản lí lớp học.<br>Hai không gian riêng, cùng một hành trình tiến bộ.</p>
 </div>
 <div class="portal-grid">
  <article class="portal-card teacher-portal" aria-labelledby="teacherPortalTitle">
   <div class="portal-heading">
    <div class="portal-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16v11H4zM8 20l4-5 4 5M8 8h8M8 11h5"/></svg></div>
    <div><p class="portal-eyebrow">KHÔNG GIAN GIẢNG DẠY</p><h2 id="teacherPortalTitle">Giáo viên</h2></div>
   </div>
   <p class="portal-description">Quản lí lớp bạn dạy, theo dõi kết quả và hỗ trợ từng học sinh.</p>
   <ul class="portal-features" aria-label="Chức năng giáo viên"><li>Quản lí lớp học</li><li>Theo dõi tiến độ</li><li>Báo cáo học sinh</li></ul>
   <form id="teacherLoginForm" class="portal-form" onsubmit="event.preventDefault();login('teacher')">
    <div class="field"><label for="teacherLoginUser">Tên đăng nhập giáo viên</label><input id="teacherLoginUser" name="username" autocomplete="username" autocapitalize="none" spellcheck="false" required maxlength="64" placeholder="Tài khoản giáo viên"></div>
    <div class="field"><label for="teacherLoginPass">Mật khẩu</label><input id="teacherLoginPass" name="password" type="password" autocomplete="current-password" required maxlength="128" aria-describedby="teacherLoginMsg"></div>
    <button id="teacherLoginSubmit" class="btn portal-submit" type="submit">Đăng nhập giáo viên</button>
    <p id="teacherLoginMsg" class="portal-message" role="status" aria-live="polite"></p>
   </form>
   <p class="portal-note">Tài khoản giáo viên do quản trị viên cấp. Tài khoản quản trị cũng đăng nhập tại khu vực này.</p>
  </article>
  <article class="portal-card student-portal" aria-labelledby="studentPortalTitle">
   <div class="portal-heading">
    <div class="portal-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5.5c3-1 6-.5 9 1.5 3-2 6-2.5 9-1.5v14c-3-1-6-.5-9 1.5-3-2-6-2.5-9-1.5zM12 7v14M6 9h2M16 9h2"/></svg></div>
    <div><p class="portal-eyebrow">KHÔNG GIAN HỌC TẬP</p><h2 id="studentPortalTitle">Học sinh</h2></div>
   </div>
   <p class="portal-description">Ôn tập Vật lí, nhận diện lỗi tư duy và luyện tập theo tiến độ của bạn.</p>
   <ul class="portal-features" aria-label="Chức năng học sinh"><li>Ôn tập &amp; chẩn đoán</li><li>Luyện đề</li><li>Sửa lỗi tư duy</li></ul>
   <form id="studentLoginForm" class="portal-form" onsubmit="event.preventDefault();login('student')">
    <div class="field"><label for="studentLoginUser">Tên đăng nhập học sinh</label><input id="studentLoginUser" name="username" autocomplete="username" autocapitalize="none" spellcheck="false" required maxlength="64" placeholder="Tài khoản học sinh"></div>
    <div class="field"><label for="studentLoginPass">Mật khẩu</label><input id="studentLoginPass" name="password" type="password" autocomplete="current-password" required maxlength="128" aria-describedby="studentLoginMsg"></div>
    <button id="studentLoginSubmit" class="btn portal-submit" type="submit">Đăng nhập học sinh</button>
    <p id="studentLoginMsg" class="portal-message" role="status" aria-live="polite"></p>
   </form>
   <details id="studentRegistration" class="portal-registration">
    <summary>Chưa có tài khoản? Đăng kí học sinh</summary>
    <p class="registration-hint">Tạo tài khoản học sinh. Nhập mã lớp giáo viên cung cấp để tham gia lớp của bạn.</p>
    <form id="studentRegisterForm" onsubmit="event.preventDefault();register()">
     <div class="field"><label for="regName">Họ tên</label><input id="regName" name="display_name" autocomplete="name" required minlength="2" maxlength="120"></div>
     <div class="field"><label for="regUser">Tên đăng nhập</label><input id="regUser" name="username" autocomplete="username" autocapitalize="none" spellcheck="false" required minlength="3" maxlength="64" pattern="[a-zA-Z0-9._\\-]+" placeholder="vd: 12a1-nguyenvana" aria-describedby="regUserHint"><div id="regUserHint" class="small muted">Từ 3 kí tự; dùng chữ không dấu, số, dấu chấm, gạch dưới hoặc gạch ngang.</div></div>
     <div class="field"><label for="regPass">Mật khẩu</label><input id="regPass" name="password" type="password" autocomplete="new-password" required minlength="8" maxlength="128" aria-describedby="regPasswordHint"><div id="regPasswordHint" class="small muted">Tối thiểu 8 kí tự.</div></div>
     <div class="field"><label for="regClass">Mã lớp <span class="muted">(nếu có)</span></label><input id="regClass" name="class_code" autocomplete="off" autocapitalize="characters" maxlength="12" placeholder="Mã giáo viên cung cấp"></div>
     <button id="studentRegisterSubmit" class="btn portal-submit" type="submit">Tạo tài khoản học sinh</button>
     <p id="regMsg" class="portal-message" role="status" aria-live="polite"></p>
    </form>
   </details>
  </article>
 </div>
</section>
"""

AUTH_FUNCTIONS = """
let authPending=false;
let metaRequest=null,teacherLoadVersion=0,classRequestVersion=0,studentRequestVersion=0,schoolRequestVersion=0;
async function ensureMeta(){
 if(meta)return meta;
 if(!metaRequest)metaRequest=api('/api/meta').then(value=>{meta=value;return value}).finally(()=>{metaRequest=null});
 return metaRequest;
}
function setAuthBusy(busy,activeButton,label){
 authPending=busy;
 for(const id of ['teacherLoginSubmit','studentLoginSubmit','studentRegisterSubmit'])$(id).disabled=busy;
 if(activeButton){
  if(busy){activeButton.dataset.label=activeButton.textContent;activeButton.textContent=label}
  else{activeButton.textContent=activeButton.dataset.label;delete activeButton.dataset.label}
  activeButton.closest('form').setAttribute('aria-busy',String(busy));
 }
}
function clearAuthForms(){
 for(const id of ['teacherLoginForm','studentLoginForm','studentRegisterForm'])$(id).reset();
 for(const id of ['teacherLoginMsg','studentLoginMsg','regMsg'])$(id).textContent='';
 $('studentRegistration').open=false;
}
async function login(portal){
 if(authPending||!['teacher','student'].includes(portal))return;
 const form=$(portal+'LoginForm'),button=$(portal+'LoginSubmit'),message=$(portal+'LoginMsg');
 if(!form.reportValidity())return;
 message.textContent='';setAuthBusy(true,button,'Đang đăng nhập…');
 try{
  await ensureMeta();
  const x=await api('/api/auth/login',{method:'POST',body:JSON.stringify({
   username:$(portal+'LoginUser').value.trim().toLowerCase(),password:$(portal+'LoginPass').value,portal
  })});
  if(portal==='student'?x.user.role!=='student':!['teacher','admin'].includes(x.user.role)){
   throw new Error(portal==='student'?'Vui lòng dùng khu đăng nhập giáo viên.':'Vui lòng dùng khu đăng nhập học sinh.');
  }
  token=x.token;localStorage.setItem('phy_token',token);me=x.user;
  clearAuthForms();renderTop();routeHome(x.classes);
 }catch(e){message.textContent=e.message}
 finally{setAuthBusy(false,button)}
}
async function register(){
 if(authPending)return;
 const form=$('studentRegisterForm'),button=$('studentRegisterSubmit');
 if(!form.reportValidity())return;
 $('regMsg').textContent='';setAuthBusy(true,button,'Đang tạo tài khoản…');
 try{
  await ensureMeta();
  const x=await api('/api/auth/register',{method:'POST',body:JSON.stringify({
   display_name:$('regName').value.trim(),username:$('regUser').value.trim().toLowerCase(),
   password:$('regPass').value,class_code:$('regClass').value.trim().toUpperCase()||null
  })});
  token=x.token;localStorage.setItem('phy_token',token);me=x.user;
  clearAuthForms();renderTop();routeHome(x.classes);
 }catch(e){$('regMsg').textContent=e.message}
 finally{setAuthBusy(false,button)}
}
"""

LOGOUT = """function logout(){
 token='';me=null;currentClassId=null;currentStudentId=null;
 teacherLoadVersion++;classRequestVersion++;studentRequestVersion++;
 schoolRequestVersion++;currentSchoolId=null;teacherSchools=[];currentSchoolCode='';
 $('schoolDetailCard').classList.add('hidden');$('schoolStats').textContent='';
 if(examTimerHandle){clearInterval(examTimerHandle);examTimerHandle=null}
 localStorage.removeItem('phy_token');clearAuthForms();show('authView');renderTop();
}
"""

LOAD_TEACHER = """async function loadTeacherClassesBase(){
 const request=++teacherLoadVersion,sessionToken=token;
 classRequestVersion++;studentRequestVersion++;
 currentClassId=null;currentStudentId=null;
 $('studentDetailCard').classList.add('hidden');$('exportBtn').classList.add('hidden');
 for(const id of ['teacherStats','studentProgressRows','sessionRows','declineList','classHint','filterHint'])$(id).textContent='';
 $('classList').textContent='Đang tải lớp học…';
 try{
  initTeacherFilters();const cs=await api('/api/classes');
  if(request!==teacherLoadVersion||sessionToken!==token)return;
  $('classList').innerHTML=cs.length?cs.map(c=>`<div class="row"><div class="toolbar"><div><b>${esc(c.name)}</b><div class="small muted">Mã tham gia: ${esc(c.join_code)}</div></div><button type="button" class="btn secondary" onclick="selectClass('${c.id}')">Quản lí học sinh</button></div></div>`).join(''):'<div class="small muted">Bạn chưa có lớp học. Chọn “Tạo lớp”, sau đó gửi mã tham gia cho học sinh của mình.</div>';
  if(cs.length)await selectClass(cs[0].id);
  else{
   $('classHint').textContent='Tạo lớp để bắt đầu quản lí học sinh.';
   $('studentProgressRows').innerHTML='<tr><td colspan="12" class="muted">Học sinh sẽ xuất hiện tại đây sau khi tham gia lớp bằng mã của bạn.</td></tr>';
  }
 }catch(e){if(request===teacherLoadVersion&&sessionToken===token)$('classList').textContent=e.message}
}
"""

BOOT = """async function boot(){
 const restoreToken=token;
 try{await ensureMeta()}
 catch(e){for(const id of ['teacherLoginMsg','studentLoginMsg'])$(id).textContent='Không kết nối được máy chủ. Vui lòng thử đăng nhập lại.';return}
 if(!restoreToken||restoreToken!==token||authPending)return;
 try{
  const x=await api('/api/me');
  if(restoreToken!==token||authPending)return;
  me=x.user;renderTop();routeHome(x.classes);
 }catch(e){if(restoreToken===token&&!authPending)logout()}
}
"""

SHOW_VIEW = """function show(id){
 const target=$(id)||$('authView');
 if(!target)return;
 for(const viewId of ['authView','studentView','questionView','resultView','repairView','examView','examResultView','teacherView','adminView']){
  const view=$(viewId);if(view)view.classList.toggle('hidden',view!==target);
 }
}
"""


def replace_function(html: str, name: str, replacement: str) -> str:
    pattern = rf"^(?:async )?function {name}\([^\n]*\n"
    updated, count = re.subn(pattern, lambda _: replacement, html, count=1, flags=re.M)
    if count != 1:
        raise SystemExit(f"Role portal patch: {name} function marker not found")
    return updated


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise SystemExit(f"Role portal patch: expected one marker {old[:70]!r}")
    return source.replace(old, new, 1)


def guard_teacher_views(html: str) -> str:
    """Ignore requests superseded by another class, pupil or login session."""
    match = re.search(r"^async function selectClass\(id\)\{([^\n]*)\}\n", html, re.M)
    if not match:
        raise SystemExit("Role portal patch: selectClass function marker not found")
    body = replace_once(
        match[1],
        "currentClassId=id;currentStudentId=null;let d=await api(`/api/teacher/v2/classes/${id}/dashboard${tq()}`);",
        """currentClassId=id;currentStudentId=null;studentRequestVersion++;
 $('studentDetailCard').classList.add('hidden');$('exportBtn').classList.add('hidden');
 $('studentProgressRows').innerHTML='<tr><td colspan="12" class="muted">Đang tải học sinh…</td></tr>';
 $('teacherStats').textContent='';$('sessionRows').textContent='';$('declineList').textContent='';
 $('classHint').textContent='Đang tải lớp học…';
 const query=tq(),filterLabel='Đang lọc: '+($('teacherChapterFilter').value||'Tất cả chương')+($('teacherLessonFilter').value?' · '+$('teacherLessonFilter').value:'');
 const d=await api(`/api/teacher/v2/classes/${id}/dashboard${query}`);
 if(request!==classRequestVersion||sessionToken!==token)return;
""",
    )
    body = replace_once(
        body,
        "$('filterHint').textContent='Đang lọc: '+($('teacherChapterFilter').value||'Tất cả chương')+($('teacherLessonFilter').value?' · '+$('teacherLessonFilter').value:'');",
        "$('filterHint').textContent=filterLabel;",
    )
    html = replace_function(html, "selectClass", """async function selectClass(id){
 const request=++classRequestVersion,sessionToken=token;
 try{
""" + body + """
 }catch(e){if(request===classRequestVersion&&sessionToken===token)$('classHint').textContent=e.message}
}
""")
    match = re.search(r"^async function viewStudentProgress\(id\)\{([^\n]*)\}\n", html, re.M)
    if not match:
        raise SystemExit("Role portal patch: student detail function marker not found")
    body = replace_once(
        match[1],
        "currentStudentId=id;let d=await api(`/api/teacher/v2/students/${id}/progress${tq()}`),s=d.summary;",
        """currentStudentId=null;$('studentDetailCard').classList.add('hidden');
 const d=await api(`/api/teacher/v2/students/${id}/progress${tq()}`);
 if(request!==studentRequestVersion||sessionToken!==token||classId!==currentClassId)return;
 currentStudentId=id;const s=d.summary;
""",
    )
    return replace_function(html, "viewStudentProgress", """async function viewStudentProgress(id){
 const request=++studentRequestVersion,sessionToken=token,classId=currentClassId;
 try{
""" + body + """
 }catch(e){if(request===studentRequestVersion&&sessionToken===token)alert(e.message)}
}
""")


def guard_school_views(html: str) -> str:
    """Keep school support and ignore responses from an earlier account."""
    html = replace_once(
        html,
        "async function loadSchools(){\n if(!me||me.role!=='teacher'||!$('schoolSelect'))return;",
        "async function loadSchools(){\n if(!me||me.role!=='teacher'||!$('schoolSelect'))return;\n const sessionToken=token;",
    )
    html = replace_once(
        html,
        "teacherSchools=await api('/api/schools/mine');",
        "const schools=await api('/api/schools/mine');\n  if(sessionToken!==token)return;\n  teacherSchools=schools;",
    )
    html = replace_once(
        html,
        "}catch(e){$('schoolIdentity').textContent=e.message}",
        "}catch(e){if(sessionToken===token)$('schoolIdentity').textContent=e.message}",
    )
    html = replace_once(
        html,
        "if(!id)return;currentSchoolId=id;\n try{\n  let d=await api(`/api/teacher/schools/${id}/dashboard`),s=d.school;currentSchoolCode=s.code||'';",
        "if(!id)return;currentSchoolId=id;\n const request=++schoolRequestVersion,sessionToken=token;\n try{\n  const d=await api(`/api/teacher/schools/${id}/dashboard`);\n  if(request!==schoolRequestVersion||sessionToken!==token||id!==currentSchoolId)return;\n  const s=d.school;currentSchoolCode=s.code||'';",
    )
    html = replace_once(
        html,
        "async function loadTeacher(){\n if($('teacherWelcome')&&me)$('teacherWelcome').textContent=`Xin chào, ${me.display_name}`;\n await loadSchools();\n await loadTeacherClassesBase();",
        "async function loadTeacher(){\n const sessionToken=token;\n if($('teacherWelcome')&&me)$('teacherWelcome').textContent=`Xin chào, ${me.display_name}`;\n await loadSchools();\n if(sessionToken!==token)return;\n await loadTeacherClassesBase();",
    )
    html = replace_once(
        html,
        "$('schoolDetailCard').classList.remove('hidden');\n }catch(e){alert(e.message)}",
        "$('schoolDetailCard').classList.remove('hidden');\n }catch(e){if(request===schoolRequestVersion&&sessionToken===token)alert(e.message)}",
    )
    html = replace_once(
        html,
        "try{\n  let d=await api('/api/student/dashboard'),s=d.stats;",
        "const sessionToken=token;\n try{\n  const d=await api('/api/student/dashboard');\n  if(sessionToken!==token)return;\n  const s=d.stats;",
    )
    html = replace_once(
        html,
        "}catch(e){$('studentSchoolLine').textContent=e.message}",
        "}catch(e){if(sessionToken===token)$('studentSchoolLine').textContent=e.message}",
    )
    return html


def apply_patch(app_root: Path) -> None:
    frontend = app_root / "app/static/index.html"
    html = frontend.read_text(encoding="utf-8")
    if 'id="role-portal-styles"' in html:
        return
    html, count = re.subn(
        r'<section id="authView"[^>]*>.*?</section>',
        lambda _: AUTH_SECTION.strip(), html, count=1, flags=re.S,
    )
    if count != 1 or html.count("</head>") != 1:
        raise SystemExit("Role portal patch: auth section or head marker not found")
    html = html.replace("</head>", PORTAL_CSS + "</head>", 1)
    html = guard_teacher_views(html)
    html = guard_school_views(html)
    html = replace_once(html, "async function api(path,opt={}){opt.headers=", "async function api(path,opt={}){const requestToken=token;opt.headers=")
    html = replace_once(html, "logout();throw new Error(data.detail||'Phiên đăng nhập đã hết hạn')", "if(token===requestToken)logout();throw new Error(data.detail||'Phiên đăng nhập đã hết hạn')")
    html = replace_function(html, "register", "")
    html = replace_function(html, "login", AUTH_FUNCTIONS)
    html = replace_function(html, "logout", LOGOUT)
    html = replace_function(html, "show", SHOW_VIEW)
    html = replace_function(html, "loadTeacherClassesBase", LOAD_TEACHER)
    html = replace_function(html, "boot", BOOT)
    old_heading = '<span class="pill">TRANG GIÁO VIÊN</span><h2>Dashboard quản lý và theo dõi học tập</h2>'
    new_heading = '<span class="pill">TRANG GIÁO VIÊN</span><h2>Quản lí lớp học của bạn</h2><p class="small muted teacher-intro">Tạo lớp, chia sẻ mã tham gia và theo dõi học sinh trong lớp mình dạy.</p>'
    if old_heading not in html:
        raise SystemExit("Role portal patch: teacher heading marker not found")
    html = html.replace(old_heading, new_heading, 1)
    html = html.replace('<h2>Lớp học</h2><button class="btn secondary" onclick="createClass()">', '<h2>Lớp học của tôi</h2><button class="btn secondary" onclick="createClass()">', 1)
    frontend.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    apply_patch(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app"))
