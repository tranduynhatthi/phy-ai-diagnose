from pathlib import Path

frontend = Path('/app/app/static/index.html')
html = frontend.read_text(encoding='utf-8')

# MathJax: render TeX inline in question content.
mathjax_head = r'''<script>
window.MathJax={tex:{inlineMath:[['\\(','\\)']],processEscapes:true},options:{skipHtmlTags:['script','noscript','style','textarea','pre','code']}};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
'''
if 'tex-chtml.js' not in html:
    html = html.replace('</head>', mathjax_head + '</head>', 1)

helper = r'''
function texCore(x){
 let s=String(x??'').trim();
 const sup={'⁰':'0','¹':'1','²':'2','³':'3','⁴':'4','⁵':'5','⁶':'6','⁷':'7','⁸':'8','⁹':'9','⁺':'+','⁻':'-'};
 s=s.replace(/Ē/g,'\\overline{E}').replace(/⟨/g,'\\langle ').replace(/⟩/g,'\\rangle ');
 s=s.replace(/([A-Za-z0-9)])([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)/g,(_,b,e)=>b+'^{'+[...e].map(c=>sup[c]||c).join('')+'}');
 s=s.replace(/\^\(([^)]+)\)/g,'^{$1}').replace(/\^([+\-]?\d+|[A-Za-z])/g,'^{$1}');
 s=s.replace(/([A-Za-z])_([A-Za-zÀ-ỹ]+)/gu,(_,a,b)=>a+'_{'+(/^[A-Za-z]{1,3}$/.test(b)?'\\mathrm{'+b+'}':'\\text{'+b+'}')+'}');
 s=s.replace(/\bNA\b/g,'N_A').replace(/\b([A-Za-z])([0-9]+)\b/g,'$1_{$2}');
 s=s.replace(/×/g,'\\times ').replace(/·/g,'\\cdot ').replace(/√\s*([A-Za-z0-9]+)/g,'\\sqrt{$1}');
 const greek={'Δ':'\\Delta ','Φ':'\\Phi ','λ':'\\lambda ','ρ':'\\rho ','η':'\\eta ','ω':'\\omega ','α':'\\alpha ','β':'\\beta ','γ':'\\gamma ','π':'\\pi '};
 s=s.replace(/[ΔΦλρηωαβγπ]/g,c=>greek[c]);
 s=s.replace(/\bsin\s*/g,'\\sin ').replace(/\bcos\s*/g,'\\cos ').replace(/\btan\s*/g,'\\tan ').replace(/\bln\s*/g,'\\ln ');
 s=s.replace(/°C/g,'^{\\circ}\\mathrm{C}').replace(/°/g,'^{\\circ}');
 s=s.replace(/(\d),(?=\d)/g,'$1{,}');
 s=s.replace(/\bmol(?=\^\{|\b)/g,'\\mathrm{mol}');
 s=s.replace(/±/g,'\\pm ').replace(/</g,'\\lt ').replace(/>/g,'\\gt ').replace(/≤/g,'\\le ').replace(/≥/g,'\\ge ');
 return s.replace(/\s+/g,' ').trim();
}
function mathHtml(value){
 let raw=String(value??''), held=[];
 const hold=x=>{const k='@@M'+held.length+'@@';held.push('\\('+texCore(x)+'\\)');return k};
 raw=raw.replace(/(^|[\s(])([A-Za-zÀ-ỹΔΦλρηωαβγπ][A-Za-zÀ-ỹ0-9ΔΦλρηωαβγπ_\/()°]*\s*=\s*(?:(?:,(?=\d))|(?:\.(?=\d))|[^,;?.])+)/gu,(m,p,e)=>p+hold(e));
 raw=raw.replace(/(^|[\s(,;])((?:ΔU|Q|A|p|V|T|F|B|I|U\d?|N\d?|E|H)\s*(?:<|>|≤|≥)\s*[+\-]?\d+(?:[.,]\d+)?)/gu,(m,p,e)=>p+hold(e));
 raw=raw.replace(/(?:\d+(?:[.,]\d+)?|[A-Za-z])×10(?:\^[+\-]?\d+|[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)/g,m=>hold(m));
 raw=raw.replace(/\S*[ΔΦλρηωαβγπ√_^⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻×·=<>≤≥±]\S*/gu,m=>{
   if(/^@@M\d+@@$/.test(m))return m;
   const lead=(m.match(/^[('"“]*/)||[''])[0], trail=(m.match(/[.,;:?!)'"”]*$/)||[''])[0];
   const core=m.slice(lead.length,m.length-trail.length);
   return core?lead+hold(core)+trail:m;
 });
 let safe=esc(raw);
 return safe.replace(/@@M(\d+)@@/g,(_,i)=>held[Number(i)]);
}
function typesetMath(el){if(window.MathJax&&MathJax.typesetPromise){MathJax.typesetPromise(el?[el]:undefined).catch(()=>{})}}
'''

marker = "const $=id=>document.getElementById(id);const esc=s=>String(s??'').replace(/[&<>\"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[m]));"
if 'function mathHtml(value)' not in html:
    if marker not in html:
        raise SystemExit('math helper insertion marker not found')
    html = html.replace(marker, marker + helper, 1)

# Main question, choices and true/false statements.
html = html.replace("$('qText').textContent=q.prompt;", "$('qText').innerHTML=mathHtml(q.prompt);")
html = html.replace("<span>${esc(o)}</span>", "<span>${mathHtml(o)}</span>")
html = html.replace("${esc(s.text)}", "${mathHtml(s.text)}")
html = html.replace("<span>${esc(q.unit||'')}</span>", "<span>${mathHtml(q.unit||'')}</span>")
html = html.replace("qAnswered=false;$('qAnswer').innerHTML=answerHtml(q,'qa')", "qAnswered=false;$('qAnswer').innerHTML=answerHtml(q,'qa');typesetMath($('questionView'))")

# Repair questions and explanations.
html = html.replace("$('repairConcept').textContent=x.error.concept;$('repairContrast').textContent=x.error.contrast;", "$('repairConcept').innerHTML=mathHtml(x.error.concept);$('repairContrast').innerHTML=mathHtml(x.error.contrast);")
html = html.replace("$('repairQuestion').textContent=q.prompt;", "$('repairQuestion').innerHTML=mathHtml(q.prompt);")
html = html.replace("$('repairNext').classList.add('hidden')}", "$('repairNext').classList.add('hidden');typesetMath($('repairView'))}")

# Exam questions and review.
html = html.replace("$('examQText').textContent=q.prompt;", "$('examQText').innerHTML=mathHtml(q.prompt);")
html = html.replace("$('examAnswer').innerHTML=answerHtml(q,'ea');restoreExamAnswer(q)", "$('examAnswer').innerHTML=answerHtml(q,'ea');restoreExamAnswer(q);typesetMath($('examView'))")
html = html.replace("<div>${esc(x.question.prompt)}</div>", "<div>${mathHtml(x.question.prompt)}</div>")
html = html.replace("${esc(x.unit||'')}", "${mathHtml(x.unit||'')}")
html = html.replace("show('examResultView');loadProfile()", "show('examResultView');typesetMath($('examResultView'));loadProfile()")

# Feedback/explanations can also contain formulas.
html = html.replace("Array.isArray(r.explain)?r.explain.join(' '):esc(r.explain)", "Array.isArray(r.explain)?mathHtml(r.explain.join(' ')):mathHtml(r.explain)")
html = html.replace("${esc(r.explain||'')}", "${mathHtml(r.explain||'')}")
html = html.replace("$('qSubmit').classList.add('hidden');$('qNext').classList.remove('hidden')", "$('qSubmit').classList.add('hidden');$('qNext').classList.remove('hidden');typesetMath($('qFeedback'))")
html = html.replace("$('repairSubmit').classList.add('hidden');$('repairNext').classList.remove('hidden')", "$('repairSubmit').classList.add('hidden');$('repairNext').classList.remove('hidden');typesetMath($('repairFeedback'))")

frontend.write_text(html, encoding='utf-8')
