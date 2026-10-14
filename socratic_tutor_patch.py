"""Apply Socratic Tutor v1.6 after existing AI Coach patch. Both feature flags off by default."""
from pathlib import Path
from shutil import copyfile

p=Path("/app/app/main.py")
h=Path("/app/app/static/index.html")
for filename in ("socratic_tutor.py","sgk_physics12.py"):
    copyfile(Path("/tmp")/filename,Path("/app/app")/filename)

main=p.read_text(encoding="utf8")
if '@app.post("/api/tutor/start")' in main:
    raise SystemExit("Tutor already installed")
main+=r'''

# The tutor does not record graded answers or modify ErrorProfile.
# Only a new independent diagnosis can modify the Evidence Engine profile.
from .socratic_tutor import flag_enabled,clean_student_text,next_tutor_reply,expected_phase,MAX_TURNS,fallback_reply
from .sgk_physics12 import get_sgk_anchor
from sqlalchemy import func,text
from datetime import datetime,timedelta,timezone

def _tutor_public(s):
    m=dict(s.meta_json or {});turns=m.get("turns") or []
    return {"id":str(s.id),"status":s.status,"error_id":m.get("error_id"),
            "chapter":s.chapter,"lesson":s.lesson,"source":m.get("source"),
            "question":m.get("question") or "","phase":expected_phase(len(turns)),
            "turn":len(turns),"max_turns":MAX_TURNS,"history":turns,
            "ai_verification_count":sum(1 for t in turns if t.get("used_ai") and t.get("verdict")!="not_checked"),
            "consent":bool(m.get("consent")),"decision_authority":"Evidence Engine",
            "notice":"Đối thoại không chấm điểm; chỉ chẩn đoán lại mới cập nhật hồ sơ lỗi."}

@app.post("/api/tutor/start")
def start_tutor(req:dict,student:User=Depends(require_roles("student")),db:Session=Depends(get_db)):
    if not flag_enabled("SOCRATIC_TUTOR_ENABLED"):
        raise HTTPException(503,"Gia sư đang được kiểm thử; chưa được bật trên máy chủ.")
    code=str(req.get("error_id") or "").strip().upper()
    if code not in bank.error_by_id:
        raise HTTPException(400,"Mã lỗi nằm ngoài danh mục kiểm chứng.")
    profile=db.execute(select(ErrorProfile).where(
        ErrorProfile.user_id==student.id,ErrorProfile.error_id==code)).scalar_one_or_none()
    if profile is None or int(getattr(profile,"evidence_total",0) or 0)<2 or int(getattr(profile,"evidence_wrong",0) or 0)<1:
        raise HTTPException(409,"Chưa đủ bằng chứng độc lập; em cần chẩn đoán thêm.")
    error=bank.error_by_id[code]
    chapter=str(error.get("chapter") or "");lesson=str(error.get("lesson") or "")
    anchor=get_sgk_anchor(chapter,lesson)
    if not anchor:
        raise HTTPException(409,"Chưa có liên kết SGK đã đối chiếu cho lỗi này.")
    running=db.execute(select(LearningSession).where(
        LearningSession.user_id==student.id,LearningSession.kind=="tutor",
        LearningSession.status=="active")).scalars().all()
    for s in running:
        if (s.meta_json or {}).get("error_id")==code: return _tutor_public(s)
    if hasattr(LearningSession,"created_at"):
        count=db.execute(select(func.count()).select_from(LearningSession).where(
            LearningSession.user_id==student.id,LearningSession.kind=="tutor",
            LearningSession.created_at>=datetime.now(timezone.utc)-timedelta(days=1))).scalar_one()
        if count>=5: raise HTTPException(429,"Tối đa 5 phiên gia sư trong 24 giờ.")
    meta={"error_id":code,"source":anchor,"question":anchor["guiding_question"],
          "consent":req.get("llm_consent") is True,"turns":[],
          "audit":{"model_calls":0,"model_attempts":0,"tokens":0,"request_ids":[]}}
    s=LearningSession(user_id=student.id,kind="tutor",mode="socratic",
                      chapter=chapter,lesson=lesson,meta_json=meta)
    db.add(s);db.commit();db.refresh(s)
    return _tutor_public(s)

@app.get("/api/tutor/{session_id}")
def get_tutor(session_id:str,student:User=Depends(require_roles("student")),db:Session=Depends(get_db)):
    s=session_or_404(db,session_id,student.id)
    if s.kind!="tutor": raise HTTPException(404,"Phiên gia sư không tồn tại.")
    return _tutor_public(s)

@app.post("/api/tutor/{session_id}/reply")
def tutor_reply(session_id:str,req:dict,student:User=Depends(require_roles("student")),db:Session=Depends(get_db)):
    if not flag_enabled("SOCRATIC_TUTOR_ENABLED"):
        raise HTTPException(503,"Gia sư chưa được bật.")
    s=db.execute(select(LearningSession).where(
        LearningSession.id==session_id,LearningSession.user_id==student.id
    ).with_for_update()).scalar_one_or_none()
    if s is None or s.kind!="tutor": raise HTTPException(404,"Phiên gia sư không tồn tại.")
    if s.status!="active": raise HTTPException(409,"Phiên đã kết thúc. Hãy chẩn đoán lại.")
    m=dict(s.meta_json or {});turns=list(m.get("turns") or [])
    if type(req.get("expected_turn")) is not int or req["expected_turn"]!=len(turns):
        raise HTTPException(409,"Số lượt không khớp. Hãy tải lại phiên.")
    if len(turns)>=MAX_TURNS: raise HTTPException(409,"Đã hết lượt đối thoại.")
    try: message=clean_student_text(req.get("message"))
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    error=bank.error_by_id.get(m.get("error_id"))
    if not error: raise HTTPException(409,"Mã lỗi không còn hợp lệ.")
    next_phase=expected_phase(len(turns)+1)
    # Five *verified* steps: verify the student's final reflection too.
    phase=next_phase if next_phase!="recheck" else "reflect"
    enabled=(m.get("consent") is True and flag_enabled("SOCRATIC_TUTOR_LLM_ENABLED")
             and bool(__import__("os").environ.get("GEMINI_API_KEY","").strip()))
    audit=dict(m.get("audit") or {})
    can_call=enabled
    if enabled:
        # PostgreSQL transaction advisory lock makes the global budget atomic
        # even with several web workers and different students submitting together.
        if db.get_bind().dialect.name=="postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(6109202616)"))
        limit=max(0,min(500,int(__import__("os").environ.get("SOCRATIC_TUTOR_DAILY_AI_LIMIT","20"))))
        if hasattr(LearningSession,"created_at"):
            recent=db.execute(select(LearningSession).where(
                LearningSession.kind=="tutor",
                LearningSession.created_at>=datetime.now(timezone.utc)-timedelta(hours=24)
            )).scalars().all()
            attempts=sum(int((r.meta_json or {}).get("audit",{}).get("model_attempts") or 0) for r in recent)
        else:
            attempts=limit
        can_call=attempts<limit
    if can_call:
        # One possible Gemini API request per turn. Attempts count even if
        # provider rejects, times out, or replies with invalid JSON.
        audit["model_attempts"]=int(audit.get("model_attempts") or 0)+1
    reply=next_tutor_reply(message=message,phase=phase,error=error,
                           anchor=m.get("source"),previous_question=m.get("question") or "",
                           history=turns,consent=can_call)
    if next_phase=="recheck":
        reply["question"]=""
    turns.append({"question":m.get("question"),"student":message,
                  "feedback":reply["feedback"],"used_ai":reply["used_ai"],
                  "verdict":reply.get("verdict","not_checked"),
                  "verification_note":reply.get("verification_note","Gemini chưa kiểm chứng."),
                  "phase":expected_phase(len(turns))})
    m["turns"]=turns;m["question"]=reply["question"]
    if reply["used_ai"]:
        audit["model_calls"]=int(audit.get("model_calls") or 0)+1
        audit["tokens"]=int(audit.get("tokens") or 0)+int(reply.get("tokens") or 0)
        audit["request_ids"]=list(audit.get("request_ids") or [])[-14:]+[reply.get("request_id")]
    m["audit"]=audit;s.meta_json=m
    if len(turns)>=MAX_TURNS: s.status="finished"
    db.commit()
    return {**_tutor_public(s),"feedback":reply["feedback"],"used_ai":reply["used_ai"],
            "verdict":reply.get("verdict","not_checked"),
            "verification_note":reply.get("verification_note","Gemini chưa kiểm chứng.")}
'''
p.write_text(main,encoding="utf8")

html=h.read_text(encoding="utf8")
needle="renderAiCoach(r.ai_coach,'diagnosticAiCoach','resultProfiles');loadProfile()"
if needle not in html: raise SystemExit("AI Coach marker not found")
html=html.replace(needle,"renderAiCoach(r.ai_coach,'diagnosticAiCoach','resultProfiles');socraticLauncher(r.profiles,'resultProfiles');loadProfile()",1)
exam="renderAiCoach(r.ai_coach,'examAiCoach','examDiagnosis');"
if exam in html:
    html=html.replace(exam,exam+"socraticLauncher((r.post_exam_diagnosis||{}).profiles||[],'examDiagnosis');",1)
if 'id="socratic-script-v16"' in html: raise SystemExit("Socratic UI already installed")
html=html.replace("</head>",'''<style>
#socraticLayer{position:fixed;inset:0;z-index:9998;background:#12223ba8;display:none;align-items:center;justify-content:center;padding:14px}
#socraticCard{background:white;border-radius:16px;padding:22px;max-width:720px;width:100%;max-height:95vh;overflow:auto}
#socraticHistory{display:grid;gap:10px;max-height:40vh;overflow:auto;margin:16px 0}
.socraticItem{background:#eef5ff;border-radius:10px;padding:11px;white-space:pre-wrap}
.socraticItem.student{background:#fff4e7}#socraticInput{width:100%;min-height:100px;resize:vertical}
.socraticBar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:12px 0}
</style></head>''',1)
html=html.replace("</body>",r'''<div id="socraticLayer" role="dialog" aria-modal="true" aria-labelledby="socraticTitle"><div id="socraticCard">
<div class="socraticBar"><h2 id="socraticTitle">✨ AI gia sư Socratic</h2><button class="btn secondary" type="button" onclick="socraticClose()">Đóng ✕</button></div>
<p class="small muted" id="socraticSource"></p><p class="small muted">Gemini kiểm chứng lập luận theo học liệu nội bộ đã rà soát, không phải toàn văn SGK. Nhận xét AI chỉ là tạm thời; Evidence Engine quyết định sau chẩn đoán lại.</p>
<div id="socraticHistory" aria-live="polite"></div><label for="socraticInput">Em hãy giải thích cách nghĩ:</label>
<textarea id="socraticInput" maxlength="700" placeholder="Trả lời câu hỏi của gia sư..."></textarea>
<p class="small muted" id="socraticProgress"></p><div class="socraticBar"><button type="button" id="socraticSend" class="btn primary" onclick="socraticSend()">Gửi lập luận</button><button type="button" id="socraticRecheck" class="btn secondary" style="display:none" onclick="socraticStartRecheck()">Chẩn đoán lại →</button></div></div></div>
<script id="socratic-script-v16">
let socraticCurrent=null;
function socraticLauncher(profiles,anchorId){
 let anchor=$(anchorId);if(!anchor)return;
 let host=$(anchorId+'Tutor');if(!host){host=document.createElement('div');host.id=anchorId+'Tutor';host.className='card';anchor.insertAdjacentElement('afterend',host)}
 let codes=(profiles||[]).map(p=>p.error_id).filter(code=>/^[A-Z0-9-]{3,40}$/.test(code||''));
 host.innerHTML=codes.length?'<h3>✨ Học cùng AI gia sư</h3><div class="small muted">Gia sư đặt câu hỏi gợi mở theo mã lỗi. Máy chủ kiểm tra bằng chứng trong Evidence Engine.</div>'+codes.slice(0,3).map(code=>'<button type="button" class="btn secondary" onclick="socraticAskConsent(\''+code+'\')">Gia sư '+esc(code)+'</button>').join(''):'<div class="small muted">Chưa đủ bằng chứng cho một lỗi cụ thể; hãy chẩn đoán thêm.</div>';
}
function socraticAskConsent(code){
 let yes=confirm('Cho phép gửi phần lập luận em nhập trong phiên này đến Gemini để tạo câu hỏi cá nhân hóa? OK: đồng ý. Hủy: dùng câu hỏi có sẵn, không gọi Gemini.');
 void socraticOpen(code,yes);
}
async function socraticOpen(code,consent){try{
 let r=await api('/api/tutor/start',{method:'POST',body:JSON.stringify({error_id:code,llm_consent:consent})});
 socraticCurrent=r;$('socraticLayer').style.display='flex';socraticRender(r)
 }catch(e){alert('Không thể mở gia sư: '+e.message)}}
function socraticClose(){$('socraticLayer').style.display='none'}
function socraticMessage(value,isStudent){let item=document.createElement('div');item.className='socraticItem'+(isStudent?' student':'');item.textContent=value;$('socraticHistory').appendChild(item)}
function socraticRender(r){
 $('socraticHistory').innerHTML='';let source=r.source||{};
 $('socraticSource').textContent=source.title?source.book+' • '+source.title+' • Trang '+source.printed_pages.join('–')+' (PDF '+source.pdf_pages.join('–')+')':'Chưa có neo SGK đã xác minh';
 (r.history||[]).forEach(t=>{socraticMessage('Gia sư: '+t.question,false);socraticMessage('Em: '+t.student,true);socraticMessage((t.used_ai?'Gemini nhận xét ('+({consistent:'Có căn cứ',needs_revision:'Cần sửa',insufficient_evidence:'Chưa đủ thông tin'}[t.verdict]||'Tạm thời')+')':'Chưa được Gemini kiểm chứng')+': '+(t.verification_note||'')+'\\n'+t.feedback,false)});
 if(r.question)socraticMessage('Gia sư: '+r.question,false);
 let done=r.status!=='active'||r.turn>=r.max_turns;
 $('socraticInput').disabled=done;$('socraticSend').disabled=done;$('socraticInput').value='';
 $('socraticRecheck').style.display=done?'inline-flex':'none';
 $('socraticProgress').textContent=(done?'Đã đủ lượt, hãy chẩn đoán lại.':'Lượt '+(r.turn+1)+'/'+r.max_turns)+
 ' • Gemini đã kiểm chứng '+(r.ai_verification_count||0)+'/'+r.turn+' lượt'+
 (r.consent?' • Đã đồng ý dùng Gemini khi máy chủ có hạn mức':' • Chế độ không gửi tới Gemini');
}
async function socraticSend(){if(!socraticCurrent)return;
 let message=$('socraticInput').value.trim();if(message.length<2){alert('Hãy nhập ít nhất 2 ký tự.');return}
 $('socraticSend').disabled=true;try{
 let r=await api('/api/tutor/'+socraticCurrent.id+'/reply',{method:'POST',body:JSON.stringify({message,expected_turn:socraticCurrent.turn})});
 socraticCurrent=r;socraticRender(r)}catch(e){alert(e.message);$('socraticSend').disabled=false}
}
async function socraticStartRecheck(){if(!socraticCurrent)return;
 try{mode='diagnostic';let r=await api('/api/practice/start',{method:'POST',body:JSON.stringify({chapter:socraticCurrent.chapter,scope:'chapter',lesson:null,mode:'diagnostic',intensity:'standard'})});
 session=r.session;questions=r.questions;qIndex=0;qAnswered=false;socraticClose();show('questionView');renderQuestion()
 }catch(e){alert('Không thể mở chẩn đoán lại: '+e.message)}
}
</script></body>''',1)
h.write_text(html,encoding="utf8")
print("Socratic Tutor v1.6 patch installed. Default feature flags are OFF.")
