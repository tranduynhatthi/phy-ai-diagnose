from pathlib import Path

p = Path('/app/app/static/index.html')
html = p.read_text(encoding='utf-8')

# Add locked-answer visual state.
if '.answer-locked' not in html:
    html = html.replace(
        '</style>',
        '''.answer-locked{opacity:.88}
.answer-locked input{cursor:not-allowed}
.answer-locked label{cursor:default}
button:disabled{opacity:.48;cursor:not-allowed;filter:saturate(.55)}
</style>''',
        1
    )

# Keep both question buttons visible; Next starts disabled.
html = html.replace(
    '<button id="qSubmit" class="btn primary" onclick="submitCurrentAnswer()">Trả lời</button><button id="qNext" class="btn primary hidden" onclick="nextQuestion()">Câu tiếp theo</button>',
    '<div class="actions" style="margin-left:auto"><button id="qSubmit" class="btn primary" onclick="submitCurrentAnswer()">Trả lời</button><button id="qNext" class="btn secondary" onclick="nextQuestion()" disabled>Câu tiếp theo</button></div>'
)

# Keep both repair buttons visible too, for consistent interaction.
html = html.replace(
    '<button id="repairSubmit" class="btn primary" onclick="submitRepair()">Trả lời</button><button id="repairNext" class="btn primary hidden" onclick="nextRepair()">Câu tiếp theo</button>',
    '<div class="actions"><button id="repairSubmit" class="btn primary" onclick="submitRepair()">Trả lời</button><button id="repairNext" class="btn secondary" onclick="nextRepair()" disabled>Câu tiếp theo</button></div>'
)

old_render = '''function renderQuestion(){let q=questions[qIndex];$('qMeta').textContent=`${qIndex+1}/${questions.length} · ${q.lesson}`;$('qLevel').textContent=q.level;$('qProgress').style.width=`${Math.round(qIndex/questions.length*100)}%`;$('qText').textContent=q.prompt;$('qFeedback').innerHTML='';$('qSubmit').classList.remove('hidden');$('qNext').classList.add('hidden');qAnswered=false;$('qAnswer').innerHTML=answerHtml(q,'qa')}'''
new_render = '''function renderQuestion(){let q=questions[qIndex];$('qMeta').textContent=`${qIndex+1}/${questions.length} · ${q.lesson}`;$('qLevel').textContent=q.level;$('qProgress').style.width=`${Math.round(qIndex/questions.length*100)}%`;$('qText').textContent=q.prompt;$('qFeedback').innerHTML='';qAnswered=false;$('qSubmit').disabled=false;$('qNext').disabled=true;$('qNext').textContent=qIndex===questions.length-1?'Xem kết quả':'Câu tiếp theo';$('qAnswer').classList.remove('answer-locked');$('qAnswer').innerHTML=answerHtml(q,'qa')}'''
if old_render in html:
    html = html.replace(old_render, new_render, 1)

old_submit = '''async function submitCurrentAnswer(){if(qAnswered)return;let q=questions[qIndex],v=readAnswer(q,'qa');try{let r=await api(`/api/practice/${session.id}/answer`,{method:'POST',body:JSON.stringify({answer:{question_id:q.id,value:v}})});qAnswered=true;if(mode==='practice')$('qFeedback').innerHTML=`<div class="feedback ${r.correct?'good':'bad'}"><b>${r.correct?'Đúng':'Chưa đúng'}</b>${r.explain?`<div class="small">${Array.isArray(r.explain)?r.explain.join(' '):esc(r.explain)}</div>`:''}</div>`;$('qSubmit').classList.add('hidden');$('qNext').classList.remove('hidden')}catch(e){alert(e.message)}}'''
new_submit = '''async function submitCurrentAnswer(){if(qAnswered)return;let q=questions[qIndex],v=readAnswer(q,'qa');try{let r=await api(`/api/practice/${session.id}/answer`,{method:'POST',body:JSON.stringify({answer:{question_id:q.id,value:v}})});qAnswered=true;lockAnswer('qa',true);$('qAnswer').classList.add('answer-locked');$('qSubmit').disabled=true;$('qNext').disabled=false;if(mode==='practice')$('qFeedback').innerHTML=`<div class="feedback ${r.correct?'good':'bad'}"><b>${r.correct?'Đúng':'Chưa đúng'}</b>${r.explain?`<div class="small">${Array.isArray(r.explain)?r.explain.join(' '):esc(r.explain)}</div>`:''}</div>`}catch(e){alert(e.message)}}'''
if old_submit in html:
    html = html.replace(old_submit, new_submit, 1)

old_next = '''async function nextQuestion(){if(qIndex<questions.length-1){qIndex++;renderQuestion()}else await finishPractice()}'''
new_next = '''async function nextQuestion(){if(!qAnswered)return;if(qIndex<questions.length-1){qIndex++;renderQuestion()}else await finishPractice()}'''
if old_next in html:
    html = html.replace(old_next, new_next, 1)

# Helper disables every control belonging to the submitted answer.
if 'function lockAnswer(prefix,locked)' not in html:
    marker = '''function readAnswer(q,prefix){'''
    helper = '''function lockAnswer(prefix,locked){document.querySelectorAll(`#qAnswer input[name="${prefix}"],#qAnswer input[name^="${prefix}-"],#qAnswer #${prefix}-short,#repairAnswer input[name="${prefix}"],#repairAnswer input[name^="${prefix}-"],#repairAnswer #${prefix}-short`).forEach(el=>el.disabled=locked)}
'''
    if marker not in html:
        raise SystemExit('readAnswer marker not found')
    html = html.replace(marker, helper + marker, 1)

old_repair_render = '''function renderRepair(){let q=repair.questions[repairIndex];$('repairProgress').style.width=`${Math.round(repairIndex/repair.questions.length*100)}%`;$('repairMeta').textContent=`${repairIndex+1}/${repair.questions.length}`;$('repairQuestion').textContent=q.prompt;$('repairAnswer').innerHTML=answerHtml(q,'ra');$('repairFeedback').innerHTML='';$('repairSubmit').classList.remove('hidden');$('repairNext').classList.add('hidden')}'''
new_repair_render = '''function renderRepair(){let q=repair.questions[repairIndex];$('repairProgress').style.width=`${Math.round(repairIndex/repair.questions.length*100)}%`;$('repairMeta').textContent=`${repairIndex+1}/${repair.questions.length}`;$('repairQuestion').textContent=q.prompt;$('repairAnswer').innerHTML=answerHtml(q,'ra');$('repairAnswer').classList.remove('answer-locked');$('repairFeedback').innerHTML='';$('repairSubmit').disabled=false;$('repairNext').disabled=true;$('repairNext').textContent=repairIndex===repair.questions.length-1?'Hoàn thành':'Câu tiếp theo'}'''
if old_repair_render in html:
    html = html.replace(old_repair_render, new_repair_render, 1)

old_repair_submit = '''async function submitRepair(){let q=repair.questions[repairIndex],v=readAnswer(q,'ra');try{let r=await api(`/api/repair/${repair.session.id}/answer`,{method:'POST',body:JSON.stringify({answer:{question_id:q.id,value:v}})});$('repairFeedback').innerHTML=`<div class="feedback ${r.correct?'good':'bad'}"><b>${r.correct?'Đúng':'Chưa đúng'}</b><div class="small">${esc(r.explain||'')}</div></div>`;$('repairSubmit').classList.add('hidden');$('repairNext').classList.remove('hidden')}catch(e){alert(e.message)}}'''
new_repair_submit = '''async function submitRepair(){if($('repairSubmit').disabled)return;let q=repair.questions[repairIndex],v=readAnswer(q,'ra');try{let r=await api(`/api/repair/${repair.session.id}/answer`,{method:'POST',body:JSON.stringify({answer:{question_id:q.id,value:v}})});lockAnswer('ra',true);$('repairAnswer').classList.add('answer-locked');$('repairFeedback').innerHTML=`<div class="feedback ${r.correct?'good':'bad'}"><b>${r.correct?'Đúng':'Chưa đúng'}</b><div class="small">${esc(r.explain||'')}</div></div>`;$('repairSubmit').disabled=true;$('repairNext').disabled=false}catch(e){alert(e.message)}}'''
if old_repair_submit in html:
    html = html.replace(old_repair_submit, new_repair_submit, 1)

p.write_text(html, encoding='utf-8')
