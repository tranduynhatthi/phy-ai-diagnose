"""Socratic Tutor integration E2E on isolated SQLite, without Gemini or production data."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["ENVIRONMENT"]="test"
os.environ["DATABASE_URL"]="sqlite://"
os.environ["SECRET_KEY"]="socratic-e2e-only-secret-not-production"
os.environ["SOCRATIC_TUTOR_LLM_ENABLED"]="false"
os.environ["LLM_ENABLED"]="false"
from app.main import app
from app.database import Base,get_db
from app.models import User,ErrorProfile,LearningSession
from app.auth import create_access_token

@pytest.fixture
def tutor_context(monkeypatch):
    monkeypatch.setenv("SOCRATIC_TUTOR_ENABLED","true")
    monkeypatch.setenv("SOCRATIC_TUTOR_LLM_ENABLED","false")
    monkeypatch.setenv("GEMINI_API_KEY","")
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal=sessionmaker(bind=engine,expire_on_commit=False)
    with SessionLocal() as db:
        users={}
        for uid,role in (("socratic_student_a","student"),("socratic_student_b","student"),("socratic_teacher","teacher")):
            user=User(id=uid,username=uid,display_name=uid,password_hash="fixture-only",role=role)
            db.add(user);users[uid]=user
        db.commit()
    def isolated_db():
        with SessionLocal() as db:yield db
    app.dependency_overrides[get_db]=isolated_db
    client=TestClient(app)
    headers={name:{"Authorization":"Bearer "+create_access_token(user)} for name,user in users.items()}
    yield client,headers,SessionLocal
    client.close()
    app.dependency_overrides.pop(get_db,None)
    engine.dispose()

def _start(client,headers,**extra):
    return client.post("/api/tutor/start",headers=headers,json={"error_id":"VLN-01","llm_consent":False,**extra})

def _set_verified_profile(sessions):
    with sessions() as db:
        db.add(ErrorProfile(user_id="socratic_student_a",error_id="VLN-01",
            evidence_total=5,evidence_wrong=2,confidence=55.0,state="Cần chú ý",
            repair_state="Chưa sửa"))
        db.commit()

def test_student_must_have_verified_evidence(tutor_context):
    client,headers,sessions=tutor_context
    assert _start(client,headers["socratic_teacher"]).status_code==403
    assert _start(client,headers["socratic_student_a"]).status_code==409
    _set_verified_profile(sessions)
    started=_start(client,headers["socratic_student_a"])
    assert started.status_code==200,started.text
    body=started.json()
    assert body["error_id"]=="VLN-01"
    assert body["source"]["lesson_number"]==1
    assert body["source"]["printed_pages"]==[6,9]
    assert body["turn"]==0 and body["status"]=="active"
    assert body["decision_authority"]=="Evidence Engine"

def test_five_turns_are_not_evidence_and_other_student_cannot_view(tutor_context):
    client,headers,sessions=tutor_context
    _set_verified_profile(sessions)
    h=headers["socratic_student_a"]
    r=_start(client,h).json()
    sid=r["id"]
    other=client.get("/api/tutor/"+sid,headers=headers["socratic_student_b"])
    assert other.status_code in (403,404)
    for turn in range(5):
        reply=client.post(f"/api/tutor/{sid}/reply",headers=h,
            json={"message":"Em nghĩ cần xem lại các phân tử có chuyển động hay không.", "expected_turn":turn})
        assert reply.status_code==200,reply.text
        data=reply.json()
        assert data["turn"]==turn+1
        assert data["decision_authority"]=="Evidence Engine"
    assert data["status"]=="finished"
    assert data["phase"]=="recheck"
    assert data["consent"] is False
    assert all(not t["used_ai"] for t in data["history"])
    too_many=client.post(f"/api/tutor/{sid}/reply",headers=h,
        json={"message":"Bài trả lời thêm","expected_turn":5})
    assert too_many.status_code==409
    with sessions() as db:
        profile=db.execute(select(ErrorProfile).where(
            ErrorProfile.user_id=="socratic_student_a",
            ErrorProfile.error_id=="VLN-01")).scalar_one()
        assert float(profile.confidence)==55.0
        assert int(profile.evidence_total)==5
        assert int(profile.evidence_wrong)==2
        lesson=db.get(LearningSession,sid)
        assert lesson.status=="finished"
        assert (lesson.meta_json or {}).get("audit",{}).get("model_calls")==0

def test_no_consent_escalation_and_optimistic_turn(tutor_context):
    client,headers,sessions=tutor_context
    _set_verified_profile(sessions)
    h=headers["socratic_student_a"]
    first=_start(client,h,llm_consent=False).json()
    second=_start(client,h,llm_consent=True).json()
    assert first["id"]==second["id"]
    assert second["consent"] is False
    invalid=client.post(f"/api/tutor/{first['id']}/reply",headers=h,
        json={"message":"Em cần suy nghĩ lại.", "expected_turn":2})
    assert invalid.status_code==409
    valid=client.post(f"/api/tutor/{first['id']}/reply",headers=h,
        json={"message":"Em cần suy nghĩ lại.", "expected_turn":0})
    assert valid.status_code==200
    stale=client.post(f"/api/tutor/{first['id']}/reply",headers=h,
        json={"message":"Em cần suy nghĩ lại.", "expected_turn":0})
    assert stale.status_code==409
