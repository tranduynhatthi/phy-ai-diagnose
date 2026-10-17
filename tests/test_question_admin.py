"""API integration for draft→review→publish, archival, privacy and XLSX imports.

Uses transient in-memory SQLite; never opens production PostgreSQL or Gemini.
"""
import io
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["ENVIRONMENT"]="test"
os.environ["DATABASE_URL"]="sqlite://"
os.environ["SECRET_KEY"]="question-admin-integration-tests-only"
from app.main import app,bank
from app.auth import create_access_token
from app.database import Base,get_db
from app.models import User
from app.question_admin_store import ManagedQuestion,read_excel,workbook_template

@pytest.fixture
def context(monkeypatch):
    monkeypatch.setenv("QUESTION_ADMIN_ENABLED","true")
    monkeypatch.setenv("QUESTION_BANK_PUBLISH_ENABLED","false")
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine,expire_on_commit=False)
    with factory() as db:
        admins={}
        for role in ("admin","teacher","student"):
            person=User(id="qa_"+role,username="qa_"+role,display_name=role,
                        password_hash="test-only",role=role)
            db.add(person);admins[role]=person
        db.commit()
        headers={role:{"Authorization":"Bearer "+create_access_token(user)}
                 for role,user in admins.items()}
    def isolated():
        with factory() as db:yield db
    app.dependency_overrides[get_db]=isolated
    client=TestClient(app)
    yield client,headers,factory,engine
    client.close();app.dependency_overrides.pop(get_db,None);engine.dispose()

def question(diagnostic=True):
    return {"chapter":"Chương I","lesson":"Bài 1","type":"mcq",
            "prompt":"Trong vật rắn, các hạt cấu tạo nên vật chuyển động như thế nào?",
            "options":["Các hạt đứng yên hoàn toàn.","Các hạt dao động quanh vị trí cân bằng.",
                       "Các hạt chuyển động tự do không giới hạn.","Mỗi hạt di chuyển đều theo đường thẳng."],
            "answer":"B","explain":"Hạt cấu tạo vật rắn vẫn chuyển động nhiệt.",
            "error":"VLN-01" if diagnostic else "",
            "diagnostic":diagnostic}

def post(c,h,source_id=None,p=None):
    return c.post("/api/admin/question-bank",headers=h,
                  json={"source_id":source_id,"question":p or question()})

def action(c,h,id,verb,revision):
    return c.post("/api/admin/question-bank/"+id+"/"+verb,
                  headers=h,json={"expected_revision":revision})

def test_admin_only_and_base_bank_unmodified(context):
    c,h,_,_=context
    for role in ("teacher","student"):
        assert c.get("/api/admin/question-bank",headers=h[role]).status_code in (403,404)
        assert post(c,h[role]).status_code in (403,404)
    meta=c.get("/api/admin/question-bank/status",headers=h["admin"])
    assert meta.status_code==200,meta.text
    assert meta.json()["base_questions"]==1000
    assert meta.json()["published_in_practice"] is False
    base=c.get("/api/admin/question-bank?status=base&limit=2",headers=h["admin"])
    assert base.status_code==200 and base.json()["total"]==1000

def test_draft_submit_approve_archive_with_versioned_history(context):
    c,h,f,engine=context;admin=h["admin"]
    created=post(c,admin);assert created.status_code==201,created.text
    x=created.json();id=x["id"]
    assert x["status"]=="draft" and x["published"] is None
    assert action(c,admin,id,"approve",1).status_code==409
    changed=c.put("/api/admin/question-bank/"+id,headers=admin,json={
        "expected_revision":1,"question":{**question(),"prompt":"Một câu đã hiệu đính: vì sao vật rắn có chuyển động nhiệt?"}})
    assert changed.status_code==200,changed.text
    assert changed.json()["revision"]==2
    assert c.put("/api/admin/question-bank/"+id,headers=admin,json={
        "expected_revision":1,"question":question()}).status_code==409
    assert action(c,admin,id,"submit",2).status_code==200
    published=action(c,admin,id,"approve",2)
    assert published.status_code==200,published.text
    assert published.json()["status"]=="published"
    vid=published.json()["published"]["id"]
    assert vid==id+"-v2"
    with f() as db:
        r=db.get(ManagedQuestion,id)
        assert len(r.history_json)==1
        assert r.published_json["id"]==vid
    archive=action(c,admin,id,"archive-request",2)
    assert archive.status_code==200
    assert action(c,admin,id,"approve",2).json()["status"]=="archived"
    with f() as db:
        r=db.get(ManagedQuestion,id)
        assert len(r.history_json)==1
        assert r.published_json["id"]==vid

def test_unreviewed_changes_never_replace_legacy_item(context):
    c,h,f,engine=context
    base=next(x for x in bank.questions if x.get("chapter")=="Chương I" and x.get("lesson")=="Bài 1")
    resp=post(c,h["admin"],source_id=base["id"])
    assert resp.status_code==201,resp.text
    draft_id=resp.json()["id"]
    assert bank.by_id[base["id"]]["id"]==base["id"]
    # Duplicate modification of same source is refused.
    assert post(c,h["admin"],source_id=base["id"]).status_code==409
    # Improper ontology mapping is rejected before it can be queued for review.
    invalid={**question(),"error":"NOT-A-REAL-ERROR"}
    assert post(c,h["admin"],p=invalid).status_code==422
    assert action(c,h["admin"],draft_id,"submit",1).status_code==200

def test_excel_atomic_validation_and_template(context):
    import openpyxl
    c,h,f,_=context
    response=c.get("/api/admin/question-bank/template.xlsx",headers=h["admin"])
    assert response.status_code==200, (response.text,[(x.path,','.join(x.methods or [])) for x in app.routes if "question-bank" in x.path])
    wb=openpyxl.load_workbook(io.BytesIO(response.content))
    sh=wb.active;header=[x.value for x in sh[1]]
    assert header[:5]==["source_id","chapter","lesson","type","prompt"]
    values={"chapter":"Chương I","lesson":"Bài 1","type":"mcq",
            "prompt":"Một câu kiểm tra chuyển động nhiệt?",
            "options":"Đứng yên|Dao động nhiệt|Không có hạt|Chỉ chuyển động tròn",
            "answer":"B","explain":"Vật rắn có chuyển động nhiệt.",
            "error":"VLN-01","diagnostic":True}
    sh.append([values.get(key) for key in header])
    b=io.BytesIO();wb.save(b)
    headers={**h["admin"],"Content-Type":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
    imported=c.post("/api/admin/question-bank/import-xlsx",headers=headers,content=b.getvalue())
    assert imported.status_code==201,imported.text
    assert imported.json()["imported"]==1
    with f() as db: assert len(db.execute(select(ManagedQuestion)).scalars().all())==1
    sh.append([None if key!="prompt" else "=A2" for key in header])
    b=io.BytesIO();wb.save(b)
    rejected=c.post("/api/admin/question-bank/import-xlsx",headers=headers,content=b.getvalue())
    assert rejected.status_code==422
    with f() as db:assert len(db.execute(select(ManagedQuestion)).scalars().all())==1

def test_question_overlay_is_opt_in_preserves_previous_versions(context):
    c,h,f,engine=context
    from app.question_admin_overlay import install_overlay
    original_pool=bank.pool
    try:
        install_overlay(bank,engine)
        new=post(c,h["admin"]);assert new.status_code==201,new.text
        id=new.json()["id"]
        before=bank.pool("Chương I","lesson","Bài 1",diagnostic_only=True)
        assert all(q["id"]!=id+"-v1" for q in before)
        assert action(c,h["admin"],id,"submit",1).status_code==200
        assert action(c,h["admin"],id,"approve",1).status_code==200
        published=bank.pool("Chương I","lesson","Bài 1",diagnostic_only=True)
        assert any(q["id"]==id+"-v1" for q in published)
        assert bank.by_id[id+"-v1"]["answer"]==1
        assert action(c,h["admin"],id,"archive-request",1).status_code==200
        still=bank.pool("Chương I","lesson","Bài 1",diagnostic_only=True)
        assert any(q["id"]==id+"-v1" for q in still)
        assert action(c,h["admin"],id,"approve",1).status_code==200
        after=bank.pool("Chương I","lesson","Bài 1",diagnostic_only=True)
        assert all(q["id"]!=id+"-v1" for q in after)
        assert bank.by_id[id+"-v1"]["answer"]==1
    finally:
        bank.pool=original_pool
        bank._question_admin_installed=False
