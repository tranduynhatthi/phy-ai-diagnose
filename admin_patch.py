from pathlib import Path
import re

main_path = Path('/app/app/main.py')
html_path = Path('/app/app/static/index.html')

main = main_path.read_text(encoding='utf-8')
html = html_path.read_text(encoding='utf-8')

# --- Backend: make inactive accounts fail clearly at login ---
old_login = '''    if not u or not verify_password(req.password,u.password_hash):
        raise HTTPException(401,"Tên đăng nhập hoặc mật khẩu không đúng")
    return {"token":create_access_token(u),"user":serialize_user(u),"classes":student_classes(db,u.id) if u.role=="student" else []}'''
new_login = '''    if not u or not verify_password(req.password,u.password_hash):
        raise HTTPException(401,"Tên đăng nhập hoặc mật khẩu không đúng")
    if not u.is_active:
        raise HTTPException(403,"Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên")
    return {"token":create_access_token(u),"user":serialize_user(u),"classes":student_classes(db,u.id) if u.role=="student" else []}'''
if old_login in main:
    main = main.replace(old_login, new_login, 1)

# --- Backend: harden role changes; users can never self-elevate ---
old_promote = '''@app.post("/api/admin/promote")
def promote(req:PromoteRequest,admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    if req.role not in ("student","teacher","admin"):raise HTTPException(400,"Role không hợp lệ")
    u=db.get(User,req.user_id)
    if not u:raise HTTPException(404,"Không tìm thấy người dùng")
    u.role=req.role;db.commit();return serialize_user(u)'''
new_promote = '''@app.post("/api/admin/promote")
def promote(req:PromoteRequest,admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    if req.role not in ("student","teacher"):
        raise HTTPException(400,"Chỉ được chuyển giữa Học sinh và Giáo viên")
    u=db.get(User,req.user_id)
    if not u: raise HTTPException(404,"Không tìm thấy người dùng")
    if u.role=="admin": raise HTTPException(403,"Không được thay đổi quyền quản trị viên")
    if u.role=="teacher" and req.role=="student":
        owned=db.execute(select(func.count()).select_from(Classroom).where(Classroom.teacher_id==u.id)).scalar_one()
        if owned:
            raise HTTPException(409,"Giáo viên đang quản lý lớp. Hãy xử lý các lớp trước khi chuyển về Học sinh")
    u.role=req.role
    db.commit();db.refresh(u)
    return serialize_user(u) | {"is_active":u.is_active,"created_at":u.created_at}'''
if old_promote in main:
    main = main.replace(old_promote, new_promote, 1)

# --- Backend: lock/unlock and password reset, admin-only ---
admin_marker = '@app.get("/api/ai/status")\n'
if '/api/admin/users/{user_id}/active' not in main:
    endpoints = '''@app.post("/api/admin/users/{user_id}/active")
def admin_set_active(user_id:str,req:dict,admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    u=db.get(User,user_id)
    if not u: raise HTTPException(404,"Không tìm thấy người dùng")
    if u.role=="admin": raise HTTPException(403,"Không được khóa/mở khóa tài khoản quản trị viên tại đây")
    active=req.get("is_active")
    if not isinstance(active,bool): raise HTTPException(400,"Thiếu trạng thái is_active")
    u.is_active=active
    db.commit();db.refresh(u)
    return serialize_user(u) | {"is_active":u.is_active,"created_at":u.created_at}

@app.post("/api/admin/users/{user_id}/reset-password")
def admin_reset_password(user_id:str,req:dict,admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    u=db.get(User,user_id)
    if not u: raise HTTPException(404,"Không tìm thấy người dùng")
    if u.role=="admin": raise HTTPException(403,"Không đặt lại mật khẩu quản trị viên tại màn hình này")
    password=str(req.get("password") or "")
    if len(password)<8 or len(password)>128:
        raise HTTPException(400,"Mật khẩu phải từ 8 đến 128 kí tự")
    u.password_hash=hash_password(password)
    db.commit()
    return {"ok":True,"user_id":u.id,"username":u.username}

'''
    if admin_marker not in main:
        raise SystemExit('admin API insertion marker not found')
    main = main.replace(admin_marker, endpoints + admin_marker, 1)

# --- Frontend: Administrator page ---
if 'id="adminView"' not in html:
    admin_section = r'''
<section id="adminView" class="hidden">
 <div class="toolbar" style="margin-bottom:14px">
  <div><span class="pill">QUẢN TRỊ VIÊN</span><h2 style="margin:8px 0 0">Quản lý tài khoản hệ thống</h2><div class="small muted">Tài khoản đăng ký mới luôn là Học sinh. Chỉ Quản trị viên mới có thể chuyển quyền sang Giáo viên.</div></div>
  <button class="btn secondary" onclick="loadAdminUsers()">Làm mới</button>
 </div>
 <div class="card">
  <div id="adminStats" class="stats"></div>
  <div class="grid2" style="margin-top:16px">
   <div class="field"><label>Tìm theo họ tên hoặc tên đăng nhập</label><input id="adminSearch" placeholder="Nhập từ khóa..." oninput="renderAdminUsers()"></div>
   <div class="field"><label>Lọc loại tài khoản</label><select id="adminRoleFilter" onchange="renderAdminUsers()"><option value="">Tất cả</option><option value="student">Học sinh</option><option value="teacher">Giáo viên</option><option value="admin">Quản trị viên</option></select></div>
  </div>
  <div class="field" style="max-width:300px"><label>Trạng thái</label><select id="adminActiveFilter" onchange="renderAdminUsers()"><option value="">Tất cả</option><option value="active">Đang hoạt động</option><option value="locked">Đã khóa</option></select></div>
 </div>
 <div class="card">
  <div class="toolbar"><h2>Danh sách tài khoản</h2><span id="adminCount" class="small muted"></span></div>
  <div class="table"><table>
   <thead><tr><th>Họ tên</th><th>Tên đăng nhập</th><th>Loại tài khoản</th><th>Trạng thái</th><th>Ngày tạo</th><th>Thao tác</th></tr></thead>
   <tbody id="adminUserRows"></tbody>
  </table></div>
 </div>
 <div class="card">
  <h3>Nguyên tắc phân quyền</h3>
  <div class="small muted">Người dùng không thể tự nâng quyền. Đăng ký công khai chỉ tạo tài khoản Học sinh. Quyền Giáo viên chỉ được cấp từ trang này bởi tài khoản Quản trị viên. Tài khoản Quản trị viên không thể bị đổi quyền hoặc khóa tại giao diện này.</div>
 </div>
</section>
'''
    if '</main>' not in html:
        raise SystemExit('main closing marker not found')
    html = html.replace('</main>', admin_section + '\n</main>', 1)

# Add adminView to the SPA view switcher.
html = html.replace(
    "['authView','studentView','questionView','resultView','repairView','examView','examResultView','teacherView']",
    "['authView','studentView','questionView','resultView','repairView','examView','examResultView','teacherView','adminView']"
)

# Route admin separately from teacher.
old_route = "function routeHome(classes=[]){if(me.role==='student'){initStudent(classes);show('studentView');loadProfile()}else{show('teacherView');loadTeacher()}}"
new_route = "function routeHome(classes=[]){if(me.role==='student'){initStudent(classes);show('studentView');loadProfile()}else if(me.role==='admin'){show('adminView');loadAdminUsers()}else{show('teacherView');loadTeacher()}}"
if old_route in html:
    html = html.replace(old_route, new_route, 1)
elif "me.role==='admin'" not in html:
    raise SystemExit('routeHome marker not found')

# Admin client functions.
if 'async function loadAdminUsers()' not in html:
    admin_js = r'''
let adminUsers=[];
function roleVi(r){return ({student:'Học sinh',teacher:'Giáo viên',admin:'Quản trị viên'})[r]||r}
function activeVi(v){return v?'Đang hoạt động':'Đã khóa'}
async function loadAdminUsers(){
 try{
  adminUsers=await api('/api/admin/users');
  let students=adminUsers.filter(x=>x.role==='student').length,teachers=adminUsers.filter(x=>x.role==='teacher').length,locked=adminUsers.filter(x=>!x.is_active).length;
  $('adminStats').innerHTML=`<div class="stat"><b>${adminUsers.length}</b><span>tài khoản</span></div><div class="stat"><b>${students}</b><span>học sinh</span></div><div class="stat"><b>${teachers}</b><span>giáo viên</span></div><div class="stat"><b>${locked}</b><span>đã khóa</span></div>`;
  renderAdminUsers();
 }catch(e){alert(e.message)}
}
function renderAdminUsers(){
 if(!$('adminUserRows'))return;
 let q=($('adminSearch').value||'').trim().toLowerCase(),rf=$('adminRoleFilter').value,af=$('adminActiveFilter').value;
 let rows=adminUsers.filter(u=>{
  if(q&&!String(u.display_name+' '+u.username).toLowerCase().includes(q))return false;
  if(rf&&u.role!==rf)return false;
  if(af==='active'&&!u.is_active)return false;
  if(af==='locked'&&u.is_active)return false;
  return true;
 });
 $('adminCount').textContent=`Hiển thị ${rows.length}/${adminUsers.length}`;
 $('adminUserRows').innerHTML=rows.map(u=>{
  let protectedAdmin=u.role==='admin';
  let roleAction=u.role==='student'
   ? `<button class="btn secondary" onclick="changeAdminRole('${u.id}','teacher','${esc(u.username)}')">Nâng thành Giáo viên</button>`
   : u.role==='teacher'
    ? `<button class="btn ghost" onclick="changeAdminRole('${u.id}','student','${esc(u.username)}')">Chuyển về Học sinh</button>`
    : '';
  let activeAction=protectedAdmin?'':`<button class="btn ghost" onclick="toggleAdminActive('${u.id}',${u.is_active?'false':'true'},'${esc(u.username)}')">${u.is_active?'Khóa':'Mở khóa'}</button>`;
  let resetAction=protectedAdmin?'':`<button class="btn ghost" onclick="adminResetPassword('${u.id}','${esc(u.username)}')">Reset mật khẩu</button>`;
  return `<tr><td><b>${esc(u.display_name)}</b></td><td>${esc(u.username)}</td><td>${esc(roleVi(u.role))}</td><td><span class="pill">${esc(activeVi(u.is_active))}</span></td><td>${u.created_at?new Date(u.created_at).toLocaleString('vi-VN'):'—'}</td><td><div class="actions" style="gap:6px;flex-wrap:wrap">${roleAction} ${activeAction} ${resetAction}</div></td></tr>`;
 }).join('')||'<tr><td colspan="6" class="muted">Không có tài khoản phù hợp.</td></tr>';
}
async function changeAdminRole(id,role,username){
 let label=role==='teacher'?'Giáo viên':'Học sinh';
 if(!confirm(`Chuyển tài khoản ${username} thành ${label}?`))return;
 try{await api('/api/admin/promote',{method:'POST',body:JSON.stringify({user_id:id,role})});await loadAdminUsers()}catch(e){alert(e.message)}
}
async function toggleAdminActive(id,isActive,username){
 if(!confirm(`${isActive?'Mở khóa':'Khóa'} tài khoản ${username}?`))return;
 try{await api(`/api/admin/users/${id}/active`,{method:'POST',body:JSON.stringify({is_active:isActive})});await loadAdminUsers()}catch(e){alert(e.message)}
}
async function adminResetPassword(id,username){
 let p=prompt(`Nhập mật khẩu mới cho ${username} (tối thiểu 8 kí tự):`);
 if(p===null)return;
 if(p.length<8){alert('Mật khẩu phải có ít nhất 8 kí tự');return}
 let p2=prompt('Nhập lại mật khẩu mới để xác nhận:');
 if(p2!==p){alert('Hai mật khẩu không khớp');return}
 try{await api(`/api/admin/users/${id}/reset-password`,{method:'POST',body:JSON.stringify({password:p})});alert('Đã đặt lại mật khẩu cho '+username)}catch(e){alert(e.message)}
}
'''
    if 'boot();' not in html:
        raise SystemExit('boot marker not found')
    html = html.replace('boot();', admin_js + '\nboot();', 1)

main_path.write_text(main, encoding='utf-8')
html_path.write_text(html, encoding='utf-8')
