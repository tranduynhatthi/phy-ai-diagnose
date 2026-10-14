from pathlib import Path
import re

ROOT = Path("/app")
APP = ROOT / "app"
main_path = APP / "main.py"
coach_path = APP / "ai_coach.py"
html_path = APP / "static" / "index.html"

coach_code = r'''from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from .config import get_settings

logger = logging.getLogger(__name__)

COACH_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "focus_errors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "error_code": {"type": "string"},
                    "what_ai_noticed": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                },
                "required": ["error_code", "what_ai_noticed", "why_it_matters"],
                "additionalProperties": False,
            },
        },
        "plan": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step": {"type": "integer"},
                    "action": {"type": "string"},
                    "why": {"type": "string"},
                    "minutes": {"type": "integer"},
                },
                "required": ["step", "action", "why", "minutes"],
                "additionalProperties": False,
            },
        },
        "self_check": {"type": "string"},
        "encouragement": {"type": "string"},
    },
    "required": ["headline", "summary", "focus_errors", "plan", "self_check", "encouragement"],
    "additionalProperties": False,
}


def _profile_view(profile: dict) -> dict:
    return {
        "error_code": str(profile.get("error_id") or profile.get("error_code") or ""),
        "title": str(profile.get("title") or ""),
        "chapter": profile.get("chapter"),
        "lesson": profile.get("lesson"),
        "state": profile.get("state"),
        "confidence": round(float(profile.get("confidence") or 0.0), 2),
        "evidence_total": int(profile.get("evidence_total") or 0),
        "evidence_wrong": int(profile.get("evidence_wrong") or 0),
        "decision_source": profile.get("decision_source"),
        "repair_state": profile.get("repair_state"),
    }


def _fallback(*, mode: str, score: float | None, profiles: list[dict], weak_chapter: str | None) -> dict:
    focus = [_profile_view(p) for p in profiles[:3]]
    if focus:
        headline = "Kế hoạch tự học theo lỗi đã được kiểm chứng"
        summary = "Hệ thống đã xác định các điểm cần ưu tiên từ bằng chứng trong bài làm. AI Coach tạm thời chưa khả dụng nên kế hoạch này do Evidence Engine tạo."
        plan = []
        for i, p in enumerate(focus[:2], 1):
            title = p.get("title") or p.get("error_code")
            plan.append({
                "step": i,
                "action": f"Sửa lỗi {title}: đọc lại khái niệm cốt lõi rồi làm bộ câu sửa lỗi.",
                "why": "Đây là lỗi đã có bằng chứng trong bài làm của em.",
                "minutes": 6,
            })
        next_step = len(plan) + 1
        plan.append({
            "step": next_step,
            "action": "Làm một phiên chẩn đoán lại ở ngữ cảnh mới.",
            "why": "Cần kiểm tra xem em đã sửa được cách suy nghĩ chứ không chỉ nhớ đáp án.",
            "minutes": 5,
        })
    elif weak_chapter:
        headline = "Chưa đủ bằng chứng để gán một lỗi cụ thể"
        summary = f"Kết quả cho thấy {weak_chapter} là phần cần ưu tiên. Hệ thống khuyên em làm chẩn đoán sâu trước khi học lại lan man."
        plan = [
            {"step": 1, "action": f"Làm chẩn đoán sâu {weak_chapter}.", "why": "Tìm đúng nguyên nhân trước khi ôn lại.", "minutes": 8},
            {"step": 2, "action": "Sửa từng lỗi được xác nhận.", "why": "Tập trung vào điểm nghẽn thay vì học lại toàn bộ.", "minutes": 7},
            {"step": 3, "action": "Làm lại một nhóm câu ở ngữ cảnh mới.", "why": "Kiểm tra khả năng chuyển giao.", "minutes": 5},
        ]
    else:
        headline = "Tiếp tục tự học theo bằng chứng"
        summary = "Phiên này chưa tạo đủ bằng chứng để kết luận một lỗi tư duy cụ thể."
        plan = [
            {"step": 1, "action": "Làm thêm một phiên chẩn đoán ngắn.", "why": "Cần thêm bằng chứng độc lập.", "minutes": 8},
            {"step": 2, "action": "Viết 1–3 câu giải thích cách em suy nghĩ.", "why": "Giúp AI phân tích nguyên nhân thay vì chỉ nhìn đáp án.", "minutes": 3},
            {"step": 3, "action": "Sửa lỗi nếu hệ thống xác nhận.", "why": "Chỉ can thiệp khi có đủ bằng chứng.", "minutes": 6},
        ]
    return {
        "used": False,
        "provider": "evidence_engine",
        "model": None,
        "request_id": None,
        "mode": "evidence_fallback",
        "decision_authority": "Evidence Engine",
        "headline": headline,
        "summary": summary,
        "focus_errors": focus,
        "plan": plan[:3],
        "self_check": "Sau khi học lại, em có giải thích được vì sao cách nghĩ cũ sai mà không nhìn đáp án không?",
        "encouragement": "Mục tiêu không phải làm thật nhiều câu, mà là sửa đúng cách suy nghĩ đang làm em mất điểm.",
    }


def generate_ai_coach(
    *,
    mode: str,
    score: float | None,
    profiles: list[dict],
    weak_chapter: str | None = None,
    chapter_scores: dict | None = None,
    reasoning_evidence: list[dict] | None = None,
) -> dict:
    settings = get_settings()
    fallback = _fallback(mode=mode, score=score, profiles=profiles, weak_chapter=weak_chapter)
    if not bool(getattr(settings, "llm_enabled", False)):
        return fallback
    if str(getattr(settings, "ai_provider", "gemini")).lower() not in {"gemini", "auto"}:
        return fallback
    key = str(getattr(settings, "gemini_api_key", "") or "")
    if not key:
        return fallback

    verified = [_profile_view(p) for p in profiles[:5]]
    valid_codes = {p["error_code"] for p in verified if p["error_code"]}
    safe_reasoning = []
    for item in reasoning_evidence or []:
        code = str(item.get("error_code") or "")
        if code not in valid_codes:
            continue
        safe_reasoning.append({
            "error_code": code,
            "evidence": str(item.get("evidence") or "")[:400],
            "strength": round(float(item.get("strength") or 0.0), 3),
        })

    payload = {
        "mode": mode,
        "score_10": score,
        "weak_chapter": weak_chapter,
        "chapter_scores": chapter_scores or {},
        "verified_error_profiles": verified,
        "validated_reasoning_signals": safe_reasoning[:8],
    }
    instructions = (
        "Bạn là AI Coach của PHY-AI DIAGNOSE dành cho học sinh Vật lí 12 trung bình và yếu. "
        "Mục tiêu là giúp học sinh tự học bằng cách giải thích ngắn gọn: em đang vướng ở đâu, vì sao điều đó cản trở việc học, "
        "và 3 bước tiếp theo có thể làm ngay trong khoảng 15–20 phút. "
        "CHỈ được xem các verified_error_profiles là lỗi đã được hệ thống kiểm chứng. "
        "validated_reasoning_signals chỉ là bằng chứng bổ sung và chỉ được nhắc nếu error_code cũng có trong verified_error_profiles. "
        "Không được tạo mã lỗi mới, không suy đoán bệnh lí/tính cách/năng lực cố định, không gán nhãn học sinh 'yếu' hay 'kém'. "
        "Nếu verified_error_profiles rỗng, nói rõ chưa đủ bằng chứng để kết luận lỗi cụ thể và hướng học sinh sang chẩn đoán sâu ở weak_chapter nếu có. "
        "Không tiết lộ đáp án của câu hỏi chẩn đoán. Dùng tiếng Việt đơn giản, hỗ trợ, cụ thể. "
        "Kế hoạch phải có đúng 3 bước; tổng thời gian nên khoảng 15–20 phút. "
        "AI không có quyền quyết định hồ sơ lỗi; Evidence Engine là lớp quyết định cuối cùng."
    )

    model = str(getattr(settings, "gemini_model", "gemini-3.1-flash-lite"))
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + urlparse.quote(model, safe="-._") + ":generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": instructions}]},
        "contents": [{"role": "user", "parts": [{"text": json.dumps(payload, ensure_ascii=False)}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": COACH_SCHEMA,
            "temperature": 0.2,
            "maxOutputTokens": 900,
        },
    }
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    timeout = float(getattr(settings, "gemini_timeout_seconds", 12.0))
    retries = max(0, int(getattr(settings, "gemini_max_retries", 1)))
    last_exc: Exception | None = None

    for attempt in range(retries + 1):
        req = urlrequest.Request(
            url,
            data=raw,
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "x-goog-api-key": key,
                "x-goog-api-client": "phy-ai-diagnose-ai-coach/1.5",
            },
        )
        try:
            with urlrequest.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                request_id = (
                    resp.headers.get("x-request-id")
                    or resp.headers.get("x-goog-request-id")
                    or data.get("responseId")
                )
                candidates = data.get("candidates") or []
                parts = (((candidates[0] if candidates else {}) or {}).get("content") or {}).get("parts") or []
                output_text = "".join(str(p.get("text", "")) for p in parts if isinstance(p, dict))
                parsed = json.loads(output_text or "{}")

                focus = []
                for item in parsed.get("focus_errors", []) or []:
                    code = str(item.get("error_code") or "")
                    if code not in valid_codes:
                        continue
                    source = next((p for p in verified if p["error_code"] == code), {})
                    focus.append({
                        "error_code": code,
                        "title": source.get("title") or code,
                        "confidence": source.get("confidence"),
                        "state": source.get("state"),
                        "what_ai_noticed": str(item.get("what_ai_noticed") or "")[:500],
                        "why_it_matters": str(item.get("why_it_matters") or "")[:500],
                    })

                plan = []
                for idx, item in enumerate((parsed.get("plan") or [])[:3], 1):
                    plan.append({
                        "step": idx,
                        "action": str(item.get("action") or "")[:500],
                        "why": str(item.get("why") or "")[:500],
                        "minutes": max(1, min(15, int(item.get("minutes") or 5))),
                    })
                while len(plan) < 3:
                    plan.append(fallback["plan"][min(len(plan), len(fallback["plan"]) - 1)])

                usage = data.get("usageMetadata") or {}
                return {
                    "used": True,
                    "provider": "gemini",
                    "model": data.get("modelVersion") or model,
                    "request_id": request_id,
                    "mode": "ai_coach_grounded",
                    "decision_authority": "Evidence Engine",
                    "headline": str(parsed.get("headline") or fallback["headline"])[:240],
                    "summary": str(parsed.get("summary") or fallback["summary"])[:900],
                    "focus_errors": focus,
                    "plan": plan[:3],
                    "self_check": str(parsed.get("self_check") or fallback["self_check"])[:500],
                    "encouragement": str(parsed.get("encouragement") or fallback["encouragement"])[:500],
                    "usage": {
                        "input_tokens": usage.get("promptTokenCount"),
                        "output_tokens": usage.get("candidatesTokenCount"),
                        "total_tokens": usage.get("totalTokenCount"),
                    },
                }
        except urlerror.HTTPError as exc:
            last_exc = exc
            status = int(getattr(exc, "code", 0) or 0)
            if attempt < retries and status in {408, 429, 500, 502, 503, 504}:
                time.sleep(0.25 * (attempt + 1))
                continue
            break
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(0.25 * (attempt + 1))
                continue
            break

    logger.warning("AI Coach fallback: %s", type(last_exc).__name__ if last_exc else "unknown")
    fallback["reason"] = "provider_error"
    return fallback
'''

coach_path.write_text(coach_code, encoding="utf-8")

main = main_path.read_text(encoding="utf-8")
if "from .ai_coach import generate_ai_coach" not in main:
    anchor = "from .llm_gateway import llm_gateway\n"
    if anchor not in main:
        raise SystemExit("AI coach patch: llm_gateway import not found")
    main = main.replace(anchor, anchor + "from .ai_coach import generate_ai_coach\n", 1)

# Enrich per-question AI output so the student can see what AI noticed while
# keeping it explicitly at candidate-evidence level.
old_answer = '    return {"recorded":True,"ai":ai_analysis if reasoning else None}\n'
new_answer = '''    ai_student = None
    if reasoning:
        signals = []
        for item in ai_analysis.get("candidate_errors", []) or []:
            code = str(item.get("error_code") or "")
            err = bank.error_by_id.get(code, {})
            signals.append({
                "error_code": code,
                "title": err.get("title", code),
                "strength": item.get("strength"),
                "needs_confirmation": bool(item.get("needs_confirmation", True)),
                "evidence": item.get("evidence", ""),
            })
        ai_student = {
            "used": bool(ai_analysis.get("used")),
            "provider": ai_analysis.get("provider"),
            "model": ai_analysis.get("model"),
            "request_id": ai_analysis.get("request_id"),
            "feedback": ai_analysis.get("feedback", ""),
            "signals": signals,
            "status": "candidate_evidence",
            "decision_authority": "Evidence Engine",
            "reason": ai_analysis.get("reason"),
        }
    return {"recorded":True,"ai":ai_student}
'''
if old_answer not in main:
    raise SystemExit("AI coach patch: diagnostic answer return not found")
main = main.replace(old_answer, new_answer, 1)

# Diagnostic finish: Gemini becomes a visible coach, but only after the Evidence
# Engine has created/updated the profile.
finish_pattern = re.compile(
    re.escape('    return {"session":public_session(s),"profiles":profiles}') +
    r'\s+(?=@app\.post\("/api/repair/start"\))'
)
new_finish = '''    coach_profiles = []
    reasoning_evidence = []
    if s.kind == "diagnostic":
        profile_codes = {str(p.get("error_id") or "") for p in profiles}
        for item in profiles:
            err = bank.error_by_id.get(item.get("error_id"), {})
            coach_profiles.append({
                **item,
                "title": err.get("title", item.get("error_id")),
                "chapter": err.get("chapter"),
                "lesson": err.get("lesson"),
            })
        for response in s.responses:
            ai = (response.answer_json or {}).get("ai_analysis") or {}
            if not ai.get("used"):
                continue
            for signal in ai.get("candidate_errors", []) or []:
                if str(signal.get("error_code") or "") in profile_codes:
                    reasoning_evidence.append(signal)
        ai_coach = generate_ai_coach(
            mode="diagnostic",
            score=s.score,
            profiles=coach_profiles,
            weak_chapter=s.chapter,
            chapter_scores=chapter_scores,
            reasoning_evidence=reasoning_evidence,
        )
        meta = dict(s.meta_json or {})
        meta["ai_coach_audit"] = {
            "used": ai_coach.get("used"),
            "provider": ai_coach.get("provider"),
            "model": ai_coach.get("model"),
            "request_id": ai_coach.get("request_id"),
            "decision_authority": "Evidence Engine",
        }
        s.meta_json = meta
        db.commit()
    else:
        ai_coach = None
    return {"session":public_session(s),"profiles":profiles,"ai_coach":ai_coach}

@app.post("/api/repair/start")'''
main, finish_matches = finish_pattern.subn(new_finish, main, count=1)
if finish_matches != 1:
    raise SystemExit(f"AI coach patch: finish_practice return marker matches={finish_matches}")

# Exam finish: AI summarizes only already-verified profiles and chapter scores.
old_exam_return = '    return {"session":public_session(s),"result":result,"review":review,"ability_after":recent_performance(db,student.id),"post_exam_diagnosis":{"profiles":post_exam_profiles,"weak_chapter":weak_chapter,"weak_rate":round(weak_rate,4) if weak_rate is not None else None}}\n'
new_exam_return = '''    ai_coach = generate_ai_coach(
        mode="exam",
        score=result.get("total"),
        profiles=post_exam_profiles,
        weak_chapter=weak_chapter,
        chapter_scores=chapter_scores,
        reasoning_evidence=[],
    )
    meta = dict(s.meta_json or {})
    meta["ai_coach_audit"] = {
        "used": ai_coach.get("used"),
        "provider": ai_coach.get("provider"),
        "model": ai_coach.get("model"),
        "request_id": ai_coach.get("request_id"),
        "decision_authority": "Evidence Engine",
    }
    s.meta_json = meta
    db.commit()
    return {"session":public_session(s),"result":result,"review":review,"ability_after":recent_performance(db,student.id),"post_exam_diagnosis":{"profiles":post_exam_profiles,"weak_chapter":weak_chapter,"weak_rate":round(weak_rate,4) if weak_rate is not None else None},"ai_coach":ai_coach}
'''
if old_exam_return not in main:
    raise SystemExit("AI coach patch: submit_exam return marker not found")
main = main.replace(old_exam_return, new_exam_return, 1)
main_path.write_text(main, encoding="utf-8")

html = html_path.read_text(encoding="utf-8")

if 'id="ai-coach-v15-styles"' not in html:
    styles = r'''
<style id="ai-coach-v15-styles">
.ai-live{margin-top:12px;padding:14px 15px;border-radius:14px;border:1px solid #c8d9ff;background:#f4f8ff}
.ai-live .ai-title,.ai-coach-card .ai-title{display:flex;align-items:center;gap:8px;font-weight:800;color:#20458f}
.ai-live .ai-badge,.ai-coach-card .ai-badge{display:inline-flex;padding:3px 8px;border-radius:999px;background:#e7efff;color:#20458f;font-size:11px;font-weight:800}
.ai-signal{margin-top:8px;padding:9px 10px;border-left:3px solid #6f8ed8;background:#fff;border-radius:8px}
.ai-coach-card{margin-top:18px;border:1px solid #c8d9ff;background:linear-gradient(180deg,#f7faff,#fff)}
.ai-coach-card h3{margin:8px 0 6px}.ai-coach-plan{display:grid;gap:8px;margin-top:12px}
.ai-coach-step{padding:11px 12px;border-radius:11px;background:#fff;border:1px solid var(--line)}
.ai-coach-note{margin-top:10px;padding-top:10px;border-top:1px dashed #c8d9ff;font-size:12px;color:var(--muted)}
.ai-working{display:flex;gap:8px;align-items:center;color:#365b9d}.ai-dot{width:8px;height:8px;border-radius:50%;background:#527bd0;animation:aiPulse 1s infinite alternate}
@keyframes aiPulse{from{opacity:.3;transform:scale(.8)}to{opacity:1;transform:scale(1.15)}}
</style>'''
    html = html.replace("</head>", styles + "\n</head>", 1)

# Shared visible renderer for grounded AI Coach output.
if "function renderAiCoach(" not in html:
    helper = r'''
function ensureAiCoachHost(id,anchorId){
 let host=$(id);
 if(host)return host;
 let anchor=$(anchorId);if(!anchor)return null;
 host=document.createElement('div');host.id=id;host.className='card ai-coach-card';
 anchor.insertAdjacentElement('afterend',host);return host
}
function renderAiCoach(coach,id,anchorId){
 let host=ensureAiCoachHost(id,anchorId);if(!host)return;
 if(!coach){host.innerHTML='';host.classList.add('hidden');return}
 host.classList.remove('hidden');
 let used=!!coach.used,focus=coach.focus_errors||[],plan=coach.plan||[];
 let badge=used?'Gemini + Evidence Engine':'Evidence Engine · AI dự phòng';
 host.innerHTML=`<div class="ai-title">✨ AI Coach <span class="ai-badge">${esc(badge)}</span></div>
 <h3>${esc(coach.headline||'Kế hoạch tự học của em')}</h3>
 <div class="small">${esc(coach.summary||'')}</div>
 ${focus.length?'<div style="margin-top:10px"><b>AI tập trung vào các lỗi đã được kiểm chứng</b>'+focus.map(x=>`<div class="ai-signal"><b>${esc(x.error_code)} · ${esc(x.title||'')}</b><div class="small">${esc(x.what_ai_noticed||'')}</div>${x.why_it_matters?`<div class="small muted">${esc(x.why_it_matters)}</div>`:''}</div>`).join('')+'</div>':''}
 <div class="ai-coach-plan">${plan.map(x=>`<div class="ai-coach-step"><b>Bước ${Number(x.step)||''} · ${Number(x.minutes)||5} phút</b><div>${esc(x.action||'')}</div><div class="small muted">${esc(x.why||'')}</div></div>`).join('')}</div>
 ${coach.self_check?`<div class="feedback" style="margin-top:10px"><b>Tự kiểm tra:</b> ${esc(coach.self_check)}</div>`:''}
 ${coach.encouragement?`<div class="small" style="margin-top:8px">${esc(coach.encouragement)}</div>`:''}
 <div class="ai-coach-note">AI không tự quyết định em mắc lỗi. Hồ sơ lỗi chỉ được cập nhật sau khi Evidence Engine kiểm chứng bằng nhiều bằng chứng trong bài làm.</div>`
}
function renderQuestionAI(ai){
 if(!ai){$('qFeedback').innerHTML='<div class="ai-live"><div class="ai-title">✨ AI Coach</div><div class="small">Em chưa nhập cách suy nghĩ nên AI chưa phân tích nguyên nhân. Evidence Engine vẫn ghi nhận câu trả lời để kiểm chứng lỗi.</div></div>';return}
 if(!ai.used){$('qFeedback').innerHTML=`<div class="ai-live"><div class="ai-title">✨ AI Coach <span class="ai-badge">dự phòng</span></div><div class="small">AI chưa phân tích được ở câu này. Evidence Engine vẫn tiếp tục thu thập bằng chứng; kết quả chẩn đoán không bị gián đoạn.</div></div>`;return}
 let signals=ai.signals||[];
 $('qFeedback').innerHTML=`<div class="ai-live"><div class="ai-title">✨ AI đã đọc cách em suy nghĩ <span class="ai-badge">đang kiểm chứng</span></div>
 ${ai.feedback?`<div style="margin-top:6px">${esc(ai.feedback)}</div>`:''}
 ${signals.length?signals.map(s=>`<div class="ai-signal"><b>Dấu hiệu cần kiểm chứng: ${esc(s.error_code)} · ${esc(s.title||'')}</b><div class="small">${esc(s.evidence||'')}</div><div class="small muted">Độ mạnh tín hiệu AI: ${Math.round(Number(s.strength||0)*100)}% · Chưa phải kết luận cuối cùng</div></div>`).join(''):'<div class="small muted" style="margin-top:7px">AI chưa thấy dấu hiệu đủ rõ trong phần giải thích này.</div>'}
 </div>`
}
'''
    marker = "async function submitCurrentAnswer()"
    idx = html.find(marker)
    if idx < 0:
        raise SystemExit("AI coach patch: submitCurrentAnswer marker not found in HTML")
    html = html[:idx] + helper + "\n" + html[idx:]

old_submit = """async function submitCurrentAnswer(){if(qAnswered)return;let q=questions[qIndex],v=readAnswer(q,'qa'),reasoning=mode==='diagnostic'?$('qReasoning').value.trim():null;try{let r=await api(`/api/practice/${session.id}/answer`,{method:'POST',body:JSON.stringify({answer:{question_id:q.id,value:v},reasoning})});qAnswered=true;lockAnswer('qa',true);$('qAnswer').classList.add('answer-locked');$('qSubmit').disabled=true;$('qNext').disabled=false;if(mode==='practice')$('qFeedback').innerHTML=`<div class="feedback ${r.correct?'good':'bad'}"><b>${r.correct?'Đúng':'Chưa đúng'}</b>${r.explain?`<div class="small">${Array.isArray(r.explain)?mathHtml(r.explain.join(' ')):mathHtml(r.explain)}</div>`:''}</div>`}catch(e){alert(e.message)}}"""
new_submit = """async function submitCurrentAnswer(){if(qAnswered)return;let q=questions[qIndex],v=readAnswer(q,'qa'),reasoning=mode==='diagnostic'?$('qReasoning').value.trim():null;try{if(mode==='diagnostic'&&reasoning)$('qFeedback').innerHTML='<div class="ai-live"><div class="ai-working"><span class="ai-dot"></span><b>AI đang đọc cách em suy nghĩ…</b></div><div class="small muted">AI tìm dấu hiệu; Evidence Engine sẽ kiểm chứng trước khi cập nhật hồ sơ lỗi.</div></div>';let r=await api(`/api/practice/${session.id}/answer`,{method:'POST',body:JSON.stringify({answer:{question_id:q.id,value:v},reasoning})});qAnswered=true;lockAnswer('qa',true);$('qAnswer').classList.add('answer-locked');$('qSubmit').disabled=true;$('qNext').disabled=false;if(mode==='practice')$('qFeedback').innerHTML=`<div class="feedback ${r.correct?'good':'bad'}"><b>${r.correct?'Đúng':'Chưa đúng'}</b>${r.explain?`<div class="small">${Array.isArray(r.explain)?mathHtml(r.explain.join(' ')):mathHtml(r.explain)}</div>`:''}</div>`;else renderQuestionAI(r.ai)}catch(e){alert(e.message)}}"""
if old_submit not in html:
    raise SystemExit("AI coach patch: current submitCurrentAnswer not found")
html = html.replace(old_submit, new_submit, 1)

old_finish_js = """async function finishPractice(){try{let r=await api(`/api/practice/${session.id}/finish`,{method:'POST'});$('resultScore').textContent=`${Number(r.session.score).toFixed(2)}/10`;$('resultProfiles').innerHTML=r.profiles&&r.profiles.length?r.profiles.map(p=>`<div class="row"><b>${esc(p.error_id)}</b> · ${esc(p.state)} · ${Number(p.confidence).toFixed(0)}%</div>`).join(''):'';show('resultView');loadProfile()}catch(e){alert(e.message)}}"""
new_finish_js = """async function finishPractice(){try{let r=await api(`/api/practice/${session.id}/finish`,{method:'POST'});$('resultScore').textContent=`${Number(r.session.score).toFixed(2)}/10`;$('resultProfiles').innerHTML=r.profiles&&r.profiles.length?r.profiles.map(p=>`<div class="row"><b>${esc(p.error_id)}</b> · ${esc(p.state)} · ${Number(p.confidence).toFixed(0)}%</div>`).join(''):'';show('resultView');renderAiCoach(r.ai_coach,'diagnosticAiCoach','resultProfiles');loadProfile()}catch(e){alert(e.message)}}"""
if old_finish_js not in html:
    raise SystemExit("AI coach patch: current finishPractice not found")
html = html.replace(old_finish_js, new_finish_js, 1)

# The exam result already has a diagnosis panel; append the AI Coach immediately
# after it so the student's next action is visible.
exam_anchor = "$('examDiagnosisAction').innerHTML=pd.weak_chapter?"
if exam_anchor not in html:
    raise SystemExit("AI coach patch: exam diagnosis action marker not found")
needle = ":';'"
# Insert after the full diagnosis-action assignment by locating the next review assignment.
review_marker = "$('examReview').innerHTML="
review_pos = html.find(review_marker)
if review_pos < 0:
    raise SystemExit("AI coach patch: examReview marker not found")
html = html[:review_pos] + "renderAiCoach(r.ai_coach,'examAiCoach','examDiagnosis');" + html[review_pos:]

html_path.write_text(html, encoding="utf-8")
print("AI Coach v1.5 patch applied")
