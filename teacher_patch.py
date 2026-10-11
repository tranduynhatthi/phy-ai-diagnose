from pathlib import Path

main_path = Path('/app/app/main.py')
html_path = Path('/app/app/static/index.html')

main = main_path.read_text(encoding='utf-8')
html = html_path.read_text(encoding='utf-8')

old_return = '''    return {"classroom":{"id":c.id,"name":c.name,"join_code":c.join_code},"stats":{"students":len(students),"sessions":len(sessions),"answers":sum(s.total_units for s in sessions),"errors_attention":sum(p.confidence>=40 for p in profiles)},"students":[{"id":u.id,"display_name":u.display_name,"username":u.username} for u in students],"recent_sessions":[{"id":s.id,"student":name.get(s.user_id,s.user_id),"kind":s.kind,"chapter":s.chapter,"lesson":s.lesson,"score":s.score,"finished_at":s.finished_at} for s in sessions[:100]],"top_errors":[{"student_id":p.user_id,"student":name.get(p.user_id,p.user_id),"error_id":p.error_id,"title":bank.error_by_id.get(p.error_id,{}).get("title",p.error_id),"confidence":p.confidence,"state":p.state,"repair_state":p.repair_state,"diagnostic_session_id":latest_diag.get(p.user_id)} for p in top]}'''
new_return = '''    by_student_sessions={uid:[] for uid in ids}
    by_student_profiles={uid:[] for uid in ids}
    for ss in sessions: by_student_sessions.setdefault(ss.user_id,[]).append(ss)
    for pp in profiles: by_student_profiles.setdefault(pp.user_id,[]).append(pp)
    student_progress=[]
    for u in students:
        us=by_student_sessions.get(u.id,[]); up=by_student_profiles.get(u.id,[])
        scored=[x.score for x in us if x.score is not None]
        latest_score=next((x.score for x in us if x.score is not None),None)
        counts={k:sum(1 for x in us if x.kind==k) for k in ("practice","diagnostic","repair","exam")}
        student_progress.append({
            "id":u.id,"display_name":u.display_name,"username":u.username,
            "sessions":len(us),"answers":sum(x.total_units for x in us),
            "practice":counts["practice"],"diagnostic":counts["diagnostic"],"repair":counts["repair"],"exam":counts["exam"],
            "avg_score":round(sum(scored)/len(scored),2) if scored else None,"latest_score":latest_score,
            "errors_attention":sum(1 for p in up if p.confidence>=40),
            "repaired_good":sum(1 for p in up if p.repair_state=="Đã sửa tốt"),
            "last_activity":us[0].finished_at if us else None,
        })
    return {"classroom":{"id":c.id,"name":c.name,"join_code":c.join_code},"stats":{"students":len(students),"sessions":len(sessions),"answers":sum(s.total_units for s in sessions),"errors_attention":sum(p.confidence>=40 for p in profiles)},"students":[{"id":u.id,"display_name":u.display_name,"username":u.username} for u in students],"student_progress":student_progress,"recent_sessions":[{"id":s.id,"student":name.get(s.user_id,s.user_id),"kind":s.kind,"chapter":s.chapter,"lesson":s.lesson,"score":s.score,"finished_at":s.finished_at} for s in sessions[:100]],"top_errors":[{"student_id":p.user_id,"student":name.get(p.user_id,p.user_id),"error_id":p.error_id,"title":bank.error_by_id.get(p.error_id,{}).get("title",p.error_id),"confidence":p.confidence,"state":p.state,"repair_state":p.repair_state,"diagnostic_session_id":latest_diag.get(p.user_id)} for p in top]}'''
if '/api/teacher/students/{student_id}/progress' not in main:
    if old_return not in main:
        raise SystemExit('teacher dashboard return marker not found')
    main = main.replace(old_return, new_return, 1)
    marker = '@app.get("/api/teacher/classes/{class_id}/export.csv")\n'
    endpoint = '''@app.get("/api/teacher/students/{student_id}/progress")
def teacher_student_progress(student_id:str,teacher:User=Depends(require_roles("teacher","admin")),db:Session=Depends(get_db)):
    student=db.get(User,student_id)
    if not student or student.role!="student": raise HTTPException(404,"Không tìm thấy học sinh")
    if teacher.role!="admin":
        ok=db.execute(select(Enrollment).join(Classroom,Classroom.id==Enrollment.classroom_id).where(Enrollment.user_id==student_id,Classroom.teacher_id==teacher.id)).first()
        if not ok: raise HTTPException(403,"Học sinh không thuộc lớp của giáo viên")
    sessions=db.execute(select(LearningSession).where(LearningSession.user_id==student_id,LearningSession.status=="finished").order_by(desc(LearningSession.finished_at)).limit(500)).scalars().all()
    profiles=db.execute(select(ErrorProfile).where(ErrorProfile.user_id==student_id).order_by(desc(ErrorProfile.confidence))).scalars().all()
    scored=[s.score for s in sessions if s.score is not None]
    latest_score=next((s.score for s in sessions if s.score is not None),None)
    chapters={}
    for s in sessions:
        ch=s.chapter or "Khác"
        x=chapters.setdefault(ch,{"chapter":ch,"sessions":0,"scores":[],"last_activity":None})
        x["sessions"]+=1
        if s.score is not None:x["scores"].append(s.score)
        if x["last_activity"] is None:x["last_activity"]=s.finished_at
    chapter_progress=[]
    for x in chapters.values():
        vals=x.pop("scores")
        x["avg_score"]=round(sum(vals)/len(vals),2) if vals else None
        chapter_progress.append(x)
    chapter_progress.sort(key=lambda x:x["chapter"])
    return {
        "student":{"id":student.id,"display_name":student.display_name,"username":student.username},
        "summary":{"sessions":len(sessions),"answers":sum(s.total_units for s in sessions),"avg_score":round(sum(scored)/len(scored),2) if scored else None,"latest_score":latest_score,"errors_attention":sum(1 for p in profiles if p.confidence>=40),"repaired_good":sum(1 for p in profiles if p.repair_state=="Đã sửa tốt"),"last_activity":sessions[0].finished_at if sessions else None},
        "kind_counts":{k:sum(1 for s in sessions if s.kind==k) for k in ("practice","diagnostic","repair","exam")},
        "chapter_progress":chapter_progress,
        "recent_sessions":[{"id":s.id,"kind":s.kind,"chapter":s.chapter,"lesson":s.lesson,"score":s.score,"correct_units":s.correct_units,"total_units":s.total_units,"finished_at":s.finished_at} for s in sessions[:50]],
        "errors":[{"error_id":p.error_id,"title":bank.error_by_id.get(p.error_id,{}).get("title",p.error_id),"chapter":bank.error_by_id.get(p.error_id,{}).get("chapter"),"lesson":bank.error_by_id.get(p.error_id,{}).get("lesson"),"confidence":p.confidence,"state":p.state,"repair_state":p.repair_state,"evidence_wrong":p.evidence_wrong,"evidence_total":p.evidence_total} for p in profiles[:30]],
    }

'''
    if marker not in main:
        raise SystemExit('teacher export marker not found')
    main = main.replace(marker, endpoint + marker, 1)

old_teacher = '''<section id="teacherView" class="hidden">
 <div class="grid2"><div class="card"><div class="toolbar"><h2>Lớp học</h2><button class="btn secondary" onclick="createClass()">Tạo lớp</button></div><div id="classList" class="list"></div></div><div class="card"><h2>Thống kê</h2><div id="teacherStats" class="stats"></div></div></div>
 <div class="card"><div class="toolbar"><h2>Các phiên gần nhất</h2><button id="exportBtn" class="btn secondary hidden" onclick="exportClassCsv()">Xuất CSV</button></div><div class="table"><table><thead><tr><th>Học sinh</th><th>Loại</th><th>Phạm vi</th><th>Điểm</th><th>Thời gian</th></tr></thead><tbody id="sessionRows"></tbody></table></div></div>
 <div class="card"><h2>Lỗi cần chú ý</h2><div id="teacherErrors" class="list"></div></div>
</section>'''
new_teacher = '''<section id="teacherView" class="hidden">
 <div class="toolbar" style="margin-bottom:14px"><div><span class="pill">TRANG GIÁO VIÊN</span><h2 style="margin:8px 0 0">Quản lý lớp và theo dõi tiến độ học tập</h2></div><button id="exportBtn" class="btn secondary hidden" onclick="exportClassCsv()">Xuất CSV lớp</button></div>
 <div class="grid2"><div class="card"><div class="toolbar"><h2>Lớp học</h2><button class="btn secondary" onclick="createClass()">Tạo lớp</button></div><div id="classList" class="list"></div></div><div class="card"><h2>Tổng quan lớp</h2><div id="teacherStats" class="stats"></div><div id="classHint" class="small muted" style="margin-top:10px">Chọn một lớp để xem tiến độ từng học sinh.</div></div></div>
 <div class="card"><div class="toolbar"><h2>Tiến độ từng học sinh</h2><span class="small muted">Điểm chỉ phản ánh các phiên đã hoàn thành, không phải dự đoán điểm thi.</span></div><div class="table"><table><thead><tr><th>Học sinh</th><th>Tài khoản</th><th>Phiên</th><th>Ôn</th><th>Chẩn đoán</th><th>Sửa lỗi</th><th>Đề</th><th>Điểm TB</th><th>Gần nhất</th><th>Lỗi chú ý</th><th>Hoạt động cuối</th><th></th></tr></thead><tbody id="studentProgressRows"></tbody></table></div></div>
 <div id="studentDetailCard" class="card hidden"><div class="toolbar"><div><span class="pill">CHI TIẾT HỌC SINH</span><h2 id="studentDetailTitle" style="margin:8px 0 0"></h2></div><button class="btn ghost" onclick="$('studentDetailCard').classList.add('hidden')">Đóng</button></div><div id="studentDetailStats" class="stats"></div><h3>Tiến độ theo chương</h3><div class="table"><table><thead><tr><th>Chương</th><th>Số phiên</th><th>Điểm TB</th><th>Hoạt động cuối</th></tr></thead><tbody id="studentChapterRows"></tbody></table></div><h3>Lịch sử gần đây</h3><div class="table"><table><thead><tr><th>Loại</th><th>Phạm vi</th><th>Điểm</th><th>Kết quả</th><th>Thời gian</th></tr></thead><tbody id="studentSessionRows"></tbody></table></div><h3>Lỗi cần theo dõi</h3><div id="studentErrorRows" class="list"></div></div>
 <div class="card"><h2>Các phiên gần nhất của lớp</h2><div class="table"><table><thead><tr><th>Học sinh</th><th>Loại</th><th>Phạm vi</th><th>Điểm</th><th>Thời gian</th></tr></thead><tbody id="sessionRows"></tbody></table></div></div>
 <div class="card"><h2>Lỗi cần chú ý của lớp</h2><div id="teacherErrors" class="list"></div></div>
</section>'''
if 'id="studentProgressRows"' not in html:
    if old_teacher not in html:
        raise SystemExit('teacher frontend section marker not found')
    html = html.replace(old_teacher, new_teacher, 1)

old_select = '''async function selectClass(id){currentClassId=id;try{let d=await api(`/api/teacher/classes/${id}/dashboard`);$('teacherStats').innerHTML=`<div class="stat"><b>${d.stats.students}</b><span>học sinh</span></div><div class="stat"><b>${d.stats.sessions}</b><span>phiên</span></div><div class="stat"><b>${d.stats.answers}</b><span>đơn vị trả lời</span></div><div class="stat"><b>${d.stats.errors_attention}</b><span>lỗi cần chú ý</span></div>`;$('sessionRows').innerHTML=d.recent_sessions.map(s=>`<tr><td>${esc(s.student)}</td><td>${esc(s.kind)}</td><td>${esc(s.lesson||s.chapter||'')}</td><td>${s.score==null?'':Number(s.score).toFixed(2)}</td><td>${s.finished_at?new Date(s.finished_at).toLocaleString('vi-VN'):''}</td></tr>`).join('');$('teacherErrors').innerHTML=d.top_errors.map(e=>`<div class="row"><div class="toolbar"><div><b>${esc(e.student)} · ${esc(e.error_id)}</b><div class="small muted">${esc(e.title)} · ${Number(e.confidence).toFixed(0)}% · ${esc(e.state)}</div></div><div><button class="btn secondary" onclick="labelError('${e.student_id}','${e.error_id}','${e.diagnostic_session_id||''}',1)">Đúng lỗi</button> <button class="btn ghost" onclick="labelError('${e.student_id}','${e.error_id}','${e.diagnostic_session_id||''}',0)">Không phải</button></div></div></div>`).join('');$('exportBtn').classList.remove('hidden')}catch(e){alert(e.message)}}'''
new_select = '''async function selectClass(id){currentClassId=id;try{let d=await api(`/api/teacher/classes/${id}/dashboard`);$('teacherStats').innerHTML=`<div class="stat"><b>${d.stats.students}</b><span>học sinh</span></div><div class="stat"><b>${d.stats.sessions}</b><span>phiên hoàn thành</span></div><div class="stat"><b>${d.stats.answers}</b><span>đơn vị trả lời</span></div><div class="stat"><b>${d.stats.errors_attention}</b><span>lỗi cần chú ý</span></div>`;$('classHint').textContent=`${d.classroom.name} · Mã lớp: ${d.classroom.join_code}`;$('studentProgressRows').innerHTML=(d.student_progress||[]).map(s=>`<tr><td><b>${esc(s.display_name)}</b></td><td>${esc(s.username)}</td><td>${s.sessions}</td><td>${s.practice}</td><td>${s.diagnostic}</td><td>${s.repair}</td><td>${s.exam}</td><td>${s.avg_score==null?'—':Number(s.avg_score).toFixed(2)}</td><td>${s.latest_score==null?'—':Number(s.latest_score).toFixed(2)}</td><td>${s.errors_attention}</td><td>${s.last_activity?new Date(s.last_activity).toLocaleString('vi-VN'):'—'}</td><td><button class="btn secondary" onclick="viewStudentProgress('${s.id}')">Xem</button></td></tr>`).join('')||'<tr><td colspan="12" class="muted">Lớp chưa có học sinh hoặc chưa có dữ liệu.</td></tr>';$('sessionRows').innerHTML=d.recent_sessions.map(s=>`<tr><td>${esc(s.student)}</td><td>${esc(kindVi(s.kind))}</td><td>${esc(s.lesson||s.chapter||'')}</td><td>${s.score==null?'':Number(s.score).toFixed(2)}</td><td>${s.finished_at?new Date(s.finished_at).toLocaleString('vi-VN'):''}</td></tr>`).join('');$('teacherErrors').innerHTML=d.top_errors.map(e=>`<div class="row"><div class="toolbar"><div><b>${esc(e.student)} · ${esc(e.error_id)}</b><div class="small muted">${esc(e.title)} · ${Number(e.confidence).toFixed(0)}% · ${esc(e.state)}${e.repair_state?' · '+esc(e.repair_state):''}</div></div><div><button class="btn secondary" onclick="viewStudentProgress('${e.student_id}')">Xem HS</button> <button class="btn secondary" onclick="labelError('${e.student_id}','${e.error_id}','${e.diagnostic_session_id||''}',1)">Đúng lỗi</button> <button class="btn ghost" onclick="labelError('${e.student_id}','${e.error_id}','${e.diagnostic_session_id||''}',0)">Không phải</button></div></div></div>`).join('')||'<div class="small muted">Chưa có lỗi cần giáo viên chú ý.</div>';$('studentDetailCard').classList.add('hidden');$('exportBtn').classList.remove('hidden')}catch(e){alert(e.message)}}
function kindVi(k){return ({practice:'Ôn luyện',diagnostic:'Chẩn đoán',repair:'Sửa lỗi',exam:'Đề luyện'})[k]||k||''}
async function viewStudentProgress(id){try{let d=await api(`/api/teacher/students/${id}/progress`),s=d.summary;$('studentDetailTitle').textContent=`${d.student.display_name} · ${d.student.username}`;$('studentDetailStats').innerHTML=`<div class="stat"><b>${s.sessions}</b><span>phiên</span></div><div class="stat"><b>${s.avg_score==null?'—':Number(s.avg_score).toFixed(2)}</b><span>điểm TB</span></div><div class="stat"><b>${s.latest_score==null?'—':Number(s.latest_score).toFixed(2)}</b><span>điểm gần nhất</span></div><div class="stat"><b>${s.errors_attention}</b><span>lỗi cần chú ý</span></div><div class="stat"><b>${s.repaired_good}</b><span>lỗi đã sửa tốt</span></div>`;$('studentChapterRows').innerHTML=(d.chapter_progress||[]).map(x=>`<tr><td>${esc(x.chapter)}</td><td>${x.sessions}</td><td>${x.avg_score==null?'—':Number(x.avg_score).toFixed(2)}</td><td>${x.last_activity?new Date(x.last_activity).toLocaleString('vi-VN'):'—'}</td></tr>`).join('')||'<tr><td colspan="4" class="muted">Chưa có dữ liệu.</td></tr>';$('studentSessionRows').innerHTML=(d.recent_sessions||[]).map(x=>`<tr><td>${esc(kindVi(x.kind))}</td><td>${esc(x.lesson||x.chapter||'')}</td><td>${x.score==null?'—':Number(x.score).toFixed(2)}</td><td>${x.total_units?`${x.correct_units}/${x.total_units}`:'—'}</td><td>${x.finished_at?new Date(x.finished_at).toLocaleString('vi-VN'):'—'}</td></tr>`).join('')||'<tr><td colspan="5" class="muted">Chưa có phiên hoàn thành.</td></tr>';$('studentErrorRows').innerHTML=(d.errors||[]).map(e=>`<div class="row"><b>${esc(e.error_id)} · ${esc(e.title)}</b><div class="small muted">${esc(e.chapter||'')} ${e.lesson?'· '+esc(e.lesson):''} · ${Number(e.confidence).toFixed(0)}% · ${esc(e.state)}${e.repair_state?' · '+esc(e.repair_state):''}</div></div>`).join('')||'<div class="small muted">Chưa có lỗi cần theo dõi.</div>';$('studentDetailCard').classList.remove('hidden');$('studentDetailCard').scrollIntoView({behavior:'smooth',block:'start'})}catch(e){alert(e.message)}}'''
if 'function viewStudentProgress(id)' not in html:
    if old_select not in html:
        raise SystemExit('selectClass marker not found')
    html = html.replace(old_select, new_select, 1)

main_path.write_text(main, encoding='utf-8')
html_path.write_text(html, encoding='utf-8')
