from pathlib import Path

main_path=Path('/app/app/main.py')
html_path=Path('/app/app/static/index.html')
main=main_path.read_text(encoding='utf-8')
html=html_path.read_text(encoding='utf-8')

if '/api/admin/change-password' not in main:
    marker='@app.post("/api/admin/users/{user_id}/active")\n'
    endpoint='''@app.post("/api/admin/change-password")
def admin_change_password(req:dict,admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    current=str(req.get("current_password") or "")
    new_password=str(req.get("new_password") or "")
    if not verify_password(current,admin.password_hash):
        raise HTTPException(400,"Mật khẩu hiện tại không đúng")
    if len(new_password)<10 or len(new_password)>128:
        raise HTTPException(400,"Mật khẩu mới phải từ 10 đến 128 kí tự")
    if current==new_password:
        raise HTTPException(400,"Mật khẩu mới phải khác mật khẩu hiện tại")
    admin.password_hash=hash_password(new_password)
    db.commit()
    return {"ok":True,"message":"Đổi mật khẩu quản trị viên thành công"}

'''
    if marker not in main:
        raise SystemExit('admin password API insertion marker not found')
    main=main.replace(marker,endpoint+marker,1)

if 'id="adminChangePasswordCard"' not in html:
    marker=''' <div class="card">
  <h3>Nguyên tắc phân quyền</h3>'''
    card=''' <div id="adminChangePasswordCard" class="card">
  <div class="toolbar"><div><h3 style="margin:0">Đổi mật khẩu quản trị viên</h3><div class="small muted">Đổi mật khẩu của chính tài khoản Admin đang đăng nhập.</div></div></div>
  <div class="grid2">
   <div class="field"><label>Mật khẩu hiện tại</label><input id="adminCurrentPassword" type="password" autocomplete="current-password"></div>
   <div class="field"><label>Mật khẩu mới</label><input id="adminNewPassword" type="password" autocomplete="new-password"><div class="small muted">Tối thiểu 10 kí tự.</div></div>
  </div>
  <div class="field" style="max-width:520px"><label>Nhập lại mật khẩu mới</label><input id="adminNewPassword2" type="password" autocomplete="new-password"></div>
  <button class="btn secondary" onclick="changeOwnAdminPassword()">Đổi mật khẩu quản trị viên</button>
 </div>
'''
    if marker not in html:
        raise SystemExit('admin page insertion marker not found')
    html=html.replace(marker,card+marker,1)

if 'async function changeOwnAdminPassword()' not in html:
    marker='''async function adminResetPassword(id,username){
'''
    fn='''async function changeOwnAdminPassword(){
 let current=$('adminCurrentPassword').value,newp=$('adminNewPassword').value,newp2=$('adminNewPassword2').value;
 if(!current){alert('Vui lòng nhập mật khẩu hiện tại');return}
 if(newp.length<10){alert('Mật khẩu mới phải có ít nhất 10 kí tự');return}
 if(newp!==newp2){alert('Hai lần nhập mật khẩu mới không khớp');return}
 if(current===newp){alert('Mật khẩu mới phải khác mật khẩu hiện tại');return}
 if(!confirm('Đổi mật khẩu quản trị viên? Sau khi đổi, nên đăng xuất và đăng nhập lại bằng mật khẩu mới.'))return;
 try{
  await api('/api/admin/change-password',{method:'POST',body:JSON.stringify({current_password:current,new_password:newp})});
  $('adminCurrentPassword').value='';$('adminNewPassword').value='';$('adminNewPassword2').value='';
  alert('Đổi mật khẩu thành công. Hệ thống sẽ đăng xuất để thầy đăng nhập lại bằng mật khẩu mới.');
  logout();
 }catch(e){alert(e.message)}
}
'''
    if marker not in html:
        raise SystemExit('admin reset password function marker not found')
    html=html.replace(marker,fn+marker,1)

main_path.write_text(main,encoding='utf-8')
html_path.write_text(html,encoding='utf-8')
