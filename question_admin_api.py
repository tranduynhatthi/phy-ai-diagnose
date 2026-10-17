"""Admin-only question-management routes; imported into assembled FastAPI main."""
from __future__ import annotations
import copy
import os
from datetime import datetime,timezone
from sqlalchemy import select
from fastapi import Response as QAResponse, Request as QARequest
from .question_admin_store import (ManagedQuestion,new_id,version_id,normalize_question,
                                   read_excel,workbook_template)
from .question_admin_overlay import install_overlay

def _qa_enabled():
    if os.getenv("QUESTION_ADMIN_ENABLED","false").lower() not in ("1","true","yes","on"):
        raise HTTPException(503,"Quản trị ngân hàng câu hỏi chưa được bật.")

def _qa_setup(db):
    _qa_enabled()
    ManagedQuestion.__table__.create(bind=db.get_bind(),checkfirst=True)

def _qa_public(row,include_data=False):
    out={"id":row.id,"source_id":row.source_id,"status":row.status,
         "revision":row.revision,"published_revision":row.published_revision,
         "editor_id":row.editor_id,"approver_id":row.approver_id,
         "created_at":row.created_at,"updated_at":row.updated_at,
         "published_at":row.published_at,
         "is_published":bool(row.published_json and row.status!="archived"),
         "title":(row.draft_json or {}).get("prompt","")[:150],
         "chapter":(row.draft_json or {}).get("chapter"),
         "lesson":(row.draft_json or {}).get("lesson"),
         "type":(row.draft_json or {}).get("type"),
         "error":(row.draft_json or {}).get("error")}
    if include_data:
        out["draft"]=row.draft_json;out["published"]=row.published_json
        out["versions"]=[{"id":q.get("id"),"prompt":q.get("prompt","")[:120]}
                         for q in (row.history_json or [])]
    return out

def _qa_source(source_id,db,ignore_id=None):
    if not source_id:return None
    if not isinstance(source_id,str) or len(source_id)>80:
        raise HTTPException(400,"Mã câu gốc không hợp lệ.")
    if source_id not in {q.get("id") for q in bank.questions}:
        raise HTTPException(400,"Câu gốc không nằm trong ngân hàng 1.000 câu.")
    existing=db.execute(select(ManagedQuestion).where(
        ManagedQuestion.source_id==source_id)).scalars().all()
    if any(r.id!=ignore_id for r in existing):
        raise HTTPException(409,"Câu gốc đã có phiên bản quản trị. Hãy sửa bản hiện có.")
    return source_id

def _qa_record(db,qid):
    row=db.execute(select(ManagedQuestion).where(
        ManagedQuestion.id==qid).with_for_update()).scalar_one_or_none()
    if row is None: raise HTTPException(404,"Không tìm thấy bản quản trị.")
    return row

def _qa_validate(payload):
    try:return normalize_question(payload,bank)
    except (ValueError,TypeError,OverflowError) as exc:raise HTTPException(422,str(exc)) from exc

def _qa_revision(row,req):
    n=req.get("expected_revision")
    if type(n) is not int or n!=row.revision:
        raise HTTPException(409,"Phiên bản đã thay đổi; tải lại để tránh ghi đè dữ liệu.")

@app.get("/api/admin/question-bank/status")
def qa_status(admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    _qa_setup(db)
    return {"enabled":True,
            "published_in_practice":os.getenv("QUESTION_BANK_PUBLISH_ENABLED","false").lower() in ("true","1","yes","on"),
            "base_questions":len(bank.questions),"ontology_errors":len(bank.error_by_id)}

@app.get("/api/admin/question-bank/ontology")
def qa_ontology(admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    _qa_setup(db)
    return [{"id":code,"title":m.get("title") or code,
             "chapter":m.get("chapter"),"lesson":m.get("lesson")}
            for code,m in sorted(bank.error_by_id.items())]

@app.get("/api/admin/question-bank/template.xlsx")
def qa_template(admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    _qa_setup(db)
    return QAResponse(content=workbook_template(bank),
                      media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                      headers={"Content-Disposition":"attachment; filename=phyai-question-template.xlsx",
                               "Cache-Control":"no-store"})

@app.get("/api/admin/question-bank")
def qa_list(page:int=1,limit:int=30,chapter:str="",status:str="",q:str="",
            admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    _qa_setup(db)
    if page<1 or not 1<=limit<=100:raise HTTPException(400,"Trang hoặc số câu không hợp lệ.")
    managed=db.execute(select(ManagedQuestion).order_by(ManagedQuestion.updated_at.desc())).scalars().all()
    items=[_qa_public(row) for row in managed]
    sources={x.source_id for x in managed if x.source_id}
    if status in ("","base"):
        items.extend({"id":item["id"],"source_id":None,"status":"base",
                      "revision":0,"published_revision":0,
                      "title":str(item.get("prompt",""))[:150],
                      "chapter":item.get("chapter"),"lesson":item.get("lesson"),
                      "type":item.get("type"),"error":item.get("error"),
                      "is_published":True}
                     for item in bank.questions if item.get("id") not in sources)
    if status:items=[v for v in items if v["status"]==status]
    if chapter:items=[v for v in items if v["chapter"]==chapter]
    if q:
        needle=q.strip().casefold()
        items=[v for v in items if needle in (str(v["id"])+" "+str(v["title"])).casefold()]
    total=len(items);start=(page-1)*limit
    return {"items":items[start:start+limit],"total":total,"page":page,"limit":limit}

@app.get("/api/admin/question-bank/{qid}")
def qa_get(qid:str,admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    _qa_setup(db)
    row=db.get(ManagedQuestion,qid)
    if row:return _qa_public(row,True)
    base=next((v for v in bank.questions if v.get("id")==qid),None)
    if not base:raise HTTPException(404,"Không tìm thấy mã câu hỏi.")
    return {"id":qid,"source_id":qid,"status":"base","revision":0,
            "draft":copy.deepcopy(base),"published":copy.deepcopy(base)}

@app.post("/api/admin/question-bank",status_code=201)
def qa_create(req:dict,admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    _qa_setup(db)
    source=_qa_source(req.get("source_id"),db)
    obj=_qa_validate(req.get("question"))
    if source:
        before=next(q for q in bank.questions if q.get("id")==source)
        if before["chapter"]!=obj["chapter"] or before["lesson"]!=obj["lesson"]:
            raise HTTPException(422,"Không chuyển câu gốc sang bài khác; hãy tạo câu mới.")
    row=ManagedQuestion(id=new_id(),source_id=source,draft_json=obj,editor_id=admin.id,
                        status="draft",revision=1,history_json=[])
    db.add(row);db.commit();db.refresh(row)
    return _qa_public(row,True)

@app.put("/api/admin/question-bank/{qid}")
def qa_update(qid:str,req:dict,admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    _qa_setup(db)
    row=_qa_record(db,qid);_qa_revision(row,req)
    if row.status=="archived":
        raise HTTPException(409,"Bản đã xóa/ẩn; hãy tạo bản khác nếu muốn phục hồi.")
    obj=_qa_validate(req.get("question"))
    if row.source_id:
        old=next(q for q in bank.questions if q.get("id")==row.source_id)
        if old["chapter"]!=obj["chapter"] or old["lesson"]!=obj["lesson"]:
            raise HTTPException(422,"Không chuyển câu gốc sang bài khác.")
    row.draft_json=obj;row.status="draft";row.revision+=1;row.editor_id=admin.id
    db.commit();db.refresh(row);return _qa_public(row,True)

@app.post("/api/admin/question-bank/{qid}/submit")
def qa_submit(qid:str,req:dict,admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    _qa_setup(db)
    row=_qa_record(db,qid);_qa_revision(row,req)
    if row.status!="draft":raise HTTPException(409,"Chỉ gửi duyệt từ trạng thái bản nháp.")
    row.status="submitted";db.commit();db.refresh(row)
    return _qa_public(row,True)

@app.post("/api/admin/question-bank/{qid}/archive-request")
def qa_archive_request(qid:str,req:dict,admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    _qa_setup(db)
    row=_qa_record(db,qid);_qa_revision(row,req)
    if row.status=="archived":raise HTTPException(409,"Câu đã lưu trữ.")
    row.status="archive_requested";db.commit();db.refresh(row)
    return _qa_public(row,True)

@app.post("/api/admin/question-bank/{qid}/approve")
def qa_approve(qid:str,req:dict,admin:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    _qa_setup(db)
    row=_qa_record(db,qid);_qa_revision(row,req)
    if row.status not in ("submitted","archive_requested"):
        raise HTTPException(409,"Chỉ duyệt sau khi gửi duyệt hoặc yêu cầu xóa.")
    if row.status=="archive_requested":
        row.status="archived"
    else:
        # Revalidate before publishing; never publish malformed ontology mapping.
        payload=_qa_validate(row.draft_json)
        public={**payload,"id":version_id(row.id,row.revision)}
        history=list(row.history_json or []);history.append(public)
        row.history_json=history;row.published_json=public
        row.published_revision=row.revision;row.status="published"
        row.published_at=datetime.now(timezone.utc)
    row.approver_id=admin.id;db.commit();db.refresh(row)
    return _qa_public(row,True)

@app.post("/api/admin/question-bank/import-xlsx",status_code=201)
async def qa_import_xlsx(request:QARequest,admin:User=Depends(require_roles("admin")),
                         db:Session=Depends(get_db)):
    _qa_setup(db)
    if request.headers.get("content-type","").split(";")[0].lower() not in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream"):
        raise HTTPException(415,"Chỉ nhận file .xlsx, không nhận PDF, macro hoặc CSV.")
    if int(request.headers.get("content-length") or 0)>3*1024*1024:
        raise HTTPException(413,"File vượt quá 3 MB.")
    body=await request.body()
    if len(body)>3*1024*1024:raise HTTPException(413,"File vượt quá 3 MB.")
    try: parsed=read_excel(body,bank)
    except (ValueError,TypeError) as exc:raise HTTPException(422,str(exc)) from exc
    # Validate ALL source IDs before writing ANY record.
    for source,obj in parsed:
        _qa_source(source,db)
        if source:
            original=next(v for v in bank.questions if v["id"]==source)
            if obj["chapter"]!=original["chapter"] or obj["lesson"]!=original["lesson"]:
                raise HTTPException(422,f"{source}: bài/chương không trùng câu gốc.")
    rows=[]
    for source,obj in parsed:
        row=ManagedQuestion(id=new_id(),source_id=source,draft_json=obj,
                            editor_id=admin.id,status="draft",revision=1,history_json=[])
        db.add(row);rows.append(row.id)
    db.commit()
    return {"imported":len(rows),"ids":rows,"state":"draft",
            "notice":"Mọi câu nhập từ Excel chỉ là bản nháp; chưa công bố."}

# Register overlay only when explicitly enabled. This never alters the protected baseline.
if os.getenv("QUESTION_BANK_PUBLISH_ENABLED","false").lower() in ("true","1","yes","on"):
    from .question_admin_overlay import install_overlay as _qa_install
    from .database import engine as _qa_engine
    _qa_install(bank,_qa_engine)
