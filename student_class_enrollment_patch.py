"""Enable optional class enrollment for self-study students, with teacher-owned access rules.

Does not alter existing questions, results, classroom ownership, or session history.
"""
from pathlib import Path
import re

app_path=Path("/app/app/main.py")
page_path=Path("/app/app/static/index.html")
main=app_path.read_text(encoding="utf-8")
html=page_path.read_text(encoding="utf-8")

marker='@app.get("/api/ai/status")'
if main.count(marker)!=1:raise SystemExit("Expected one stable API insertion anchor")
if "/api/student/classes/join" in main:raise SystemExit("Student enrollment endpoint already exists")
api=r'''@app.post("/api/student/classes/join")
def join_teacher_class(req:dict, student:User=Depends(require_roles("student")), db:Session=Depends(get_db)):
    import re as _re
    code=str(req.get("code") or "").strip().upper()
    # Existing class code examples may use letters, numbers, dash or underscore.
    if not _re.fullmatch(r"[A-Z0-9_-]{3,16}",code):
        raise HTTPException(422,"Mã lớp phải có từ 3–16 kí tự chữ, số, - hoặc _.")
    room=db.execute(select(Classroom).where(Classroom.join_code==code)).scalar_one_or_none()
    if room is None:
        raise HTTPException(404,"Không tìm thấy lớp với mã đã nhập.")
    enrolled=db.execute(select(Enrollment).where(
        Enrollment.classroom_id==room.id,Enrollment.user_id==student.id
    )).scalar_one_or_none()
    if enrolled is None:
        db.add(Enrollment(user_id=student.id,classroom_id=room.id))
        db.commit()
    return {"ok":True,"already_joined":enrolled is not None,
            "classroom":{"id":room.id,"name":room.name}}

'''
main=main.replace(marker,api+marker,1)

hidden='<input id="regClass" type="hidden" value="">'
if html.count(hidden)!=1:raise SystemExit("Student registration class code placeholder missing")
visible='''<div class="field"><label for="regClass">Mã lớp của giáo viên (không bắt buộc)</label>
  <input id="regClass" name="class_code" autocomplete="off" autocapitalize="characters"
  maxlength="16" placeholder="Nhập mã lớp nếu giáo viên đã cung cấp">
  <div class="small muted">Chưa có mã? Vẫn có thể đăng ký và tự học bình thường; tham gia lớp sau.</div>
 </div>'''
html=html.replace(hidden,visible,1)

match=re.search(r'<section\s+id="studentView"[^>]*>',html)
if not match:raise SystemExit("Student workspace missing")
panel='''<div id="studentClassJoinPanel" class="card" style="margin:0 0 18px">
 <div class="toolbar"><div><h3 style="margin:0 0 6px">Lớp học của em</h3>
 <p class="small muted" style="margin:0">Em có thể tự học hoặc kết nối với giáo viên bằng mã tham gia lớp.</p></div></div>
 <div id="studentJoinedClasses" class="small muted" aria-live="polite">Đang tải lớp học…</div>
 <form id="studentClassJoinForm" onsubmit="event.preventDefault();joinTeacherClass()">
 <div class="grid2" style="align-items:end">
  <div class="field"><label for="studentTeacherJoinCode">Nhập mã lớp giáo viên cung cấp</label>
  <input id="studentTeacherJoinCode" maxlength="16" autocomplete="off" autocapitalize="characters" placeholder="Ví dụ: CODE_A" required></div>
  <div class="field"><button type="submit" id="studentJoinClassButton" class="btn secondary">Tham gia lớp</button></div>
 </div>
 </form>
 <p id="studentClassJoinMessage" role="status" aria-live="polite" class="small muted"></p>
</div>
'''
html=html[:match.end()]+"\n"+panel+html[match.end():]

route="if(me.role==='student'){initStudent(classes);show('studentView');loadProfile()}"
if html.count(route)!=1:raise SystemExit("Role router student case missing")
html=html.replace(route,"if(me.role==='student'){initStudent(classes);show('studentView');loadProfile();loadMyTeacherClasses()}",1)

if html.count("boot();")!=1:raise SystemExit("Application boot anchor missing")
script=r'''async function loadMyTeacherClasses(){
 const marker=token;const target=$('studentJoinedClasses');
 if(!target||!me||me.role!=='student')return;
 target.textContent='Đang tải lớp học…';
 try{
  const classes=await api('/api/classes');
  if(marker!==token||!me||me.role!=='student')return;
  target.replaceChildren();
  if(!Array.isArray(classes)||classes.length===0){
   target.textContent='Chưa tham gia lớp nào. Em vẫn có thể tự học trên hệ thống.';
   return;
  }
  for(const classroom of classes){
   const item=document.createElement('div');
   item.className='row';
   const label=document.createElement('strong');
   label.textContent=classroom.name||'Lớp học';
   item.appendChild(label);target.appendChild(item);
  }
 }catch(e){if(marker===token)target.textContent=e.message||'Không tải được danh sách lớp.'}
}
async function joinTeacherClass(){
 const field=$('studentTeacherJoinCode'),button=$('studentJoinClassButton'),msg=$('studentClassJoinMessage');
 const code=field.value.trim().toUpperCase();
 if(!/^[A-Z0-9_-]{3,16}$/.test(code)){msg.textContent='Mã lớp không hợp lệ.';return}
 if(button.disabled)return;
 button.disabled=true;msg.textContent='Đang kiểm tra mã lớp…';
 try{
  const result=await api('/api/student/classes/join',{method:'POST',body:JSON.stringify({code})});
  msg.textContent=(result.already_joined?'Em đã có trong lớp ':'Tham gia thành công lớp ')+(result.classroom?.name||'');
  field.value='';
  await loadMyTeacherClasses();
 }catch(e){msg.textContent=e.message||'Không thể tham gia lớp. Vui lòng kiểm tra mã.'}
 finally{button.disabled=false}
}
'''
html=html.replace("boot();",script+"\nboot();",1)
app_path.write_text(main,encoding="utf-8")
page_path.write_text(html,encoding="utf-8")
print("Optional student class-code enrollment restored; existing accounts can join teacher-owned classes.")
