"""Install one text/math renderer after all production frontend patches.

The renderer uses typed segments, never text sentinels or a second math renderer.
Run directly in the image, or call apply_patch(root) on an assembled application.
"""
from pathlib import Path
import re

MARKER = '<!-- PHY_AI_LATEX_UNIFIED_V3 -->'

RENDERER = r'''
function texCore(value){return phyMath.tex(String(value??''));}
function mathHtml(value,kind){return phyMath.html(String(value??''),kind);}
const phyMath=(()=>{
 const sup={'⁰':'0','¹':'1','²':'2','³':'3','⁴':'4','⁵':'5','⁶':'6','⁷':'7','⁸':'8','⁹':'9','⁺':'+','⁻':'-'};
 const sub={'₀':'0','₁':'1','₂':'2','₃':'3','₄':'4','₅':'5','₆':'6','₇':'7','₈':'8','₉':'9','₊':'+','₋':'-'};
 const greek={'Δ':'Delta','Φ':'Phi','φ':'varphi','λ':'lambda','ρ':'rho','η':'eta','ω':'omega','α':'alpha','β':'beta','γ':'gamma','θ':'theta','μ':'mu','π':'pi','σ':'sigma','ε':'varepsilon','τ':'tau','Ω':'Omega','ν':'nu'};
 const units=['nucleon','mmHg','MeV','keV','GeV','MBq','kBq','MHz','kHz','GHz','kPa','MPa','GPa','kJ','MJ','mJ','μJ','mW','kW','MW','mV','kV','mA','μA','mT','mWb','kΩ','MΩ','nm','μm','mm','cm','dm','km','mg','μg','kg','min','h','ms','μs','ns','mol','rad','sr','Hz','Pa','atm','bar','eV','Wb','Bq','Gy','Sv','mL','dB','mN','J','N','W','C','V','A','T','K','Ω','u','g','m','s','L','H'];
 const elements={H:1,He:2,Li:3,Be:4,B:5,C:6,N:7,O:8,F:9,Ne:10,Na:11,Mg:12,Al:13,Si:14,P:15,S:16,Cl:17,Ar:18,K:19,Ca:20,Fe:26,Co:27,Ni:28,Cu:29,Zn:30,Sr:38,I:53,Cs:55,Ba:56,Au:79,Hg:80,Pb:82,Bi:83,Po:84,Rn:86,Ra:88,Th:90,U:92,Pu:94};
 const letter=/[\p{L}\p{M}]/u;
 const named=['hữu ích','cung cấp','khí quyển','hóa hơi','phân rã','hạt nhân'];
 const roman=s=>'\\mathrm{'+s.replace(/μ/g,'\\mu ').replace(/Ω/g,'\\Omega ')+'}';
 const text=s=>'\\text{'+s.replace(/[{}\\%#$&]/g,c=>'\\'+c)+'}';
 const digits=(s,map)=>[...s].map(c=>map[c]??c).join('');
 const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const starts=(s,i,re)=>s.slice(i).match(re);
 function number(s,i){
  const m=starts(s,i,/^(?:\d+(?:[.,]\d+)?|[.,]\d+)(?:[eE][+\-−]?\d+)?(?:…|\.\.\.)?/u);
  if(!m)return null;
  let t=m[0].replace(/−/g,'-').replace(/,(?=\d)/g,'{,}');
  t=t.replace(/…|\.\.\./g,'\\ldots ');
  t=t.replace(/[eE]([+\-]?\d+)$/,'\\times 10^{$1}');
  return {end:i+m[0].length,tex:t,kind:'number'};
 }
 function exponent(s,i){
  const m=starts(s,i,/^(?:\^\{([^{}]+)\}|\^\(([^()]+)\)|\^([+\-−]?\d+|[A-Za-z])|([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+))/u);
  return m?{end:i+m[0].length,tex:'^{'+digits(m[1]??m[2]??m[3]??m[4],sup).replace(/−/g,'-')+'}'}:null;
 }
 function unitAtom(s,i){
  if(s.startsWith('°C',i)||s.startsWith('℃',i))return {end:i+(s[i]==='℃'?1:2),tex:'{}^{\\circ}\\mathrm{C}',kind:'unit'};
  if(s[i]==='°')return {end:i+1,tex:'{}^{\\circ}',kind:'unit'};
  if(s[i]==='%')return {end:i+1,tex:'\\%',kind:'unit'};
  for(const u of units){
   if(!s.startsWith(u,i))continue;
   const end=i+u.length;
   if(letter.test(s[end]??'')||s[end]==='_')continue;
   let a={end,tex:roman(u),kind:'unit'};
   const e=exponent(s,end);
   if(e){a.end=e.end;a.tex+=e.tex;}
   else {const n=starts(s,end,/^[23](?![\d\p{L}])/u);if(n){a.end++;a.tex+='^{'+n[0]+'}';}}
   if(/\d/.test(s[a.end]??''))continue;
   return a;
  }
  return null;
 }
 function unit(s,i){
  let first=unitAtom(s,i);if(!first)return null;
  let end=first.end,tex=first.tex;
  for(let count=0;count<8;count++){
   const join=starts(s,end,/^\s*([/·⋅.]|\s)\s*/u);if(!join)break;
   const at=end+join[0].length;
   if(join[1]==='/'&&s[at]==='('){
    const den=unit(s,at+1);if(!den||s[den.end]!==')')break;
    tex='\\frac{'+tex+'}{'+den.tex+'}';end=den.end+1;continue;
   }
   const next=unitAtom(s,at);if(!next)break;
   tex=join[1]==='/'?'\\frac{'+tex+'}{'+next.tex+'}':tex+'\\,'+next.tex;end=next.end;
  }
  return {end,tex,kind:'unit'};
 }
 function variable(s,i){
  if(s.startsWith('Eđ',i)&&!letter.test(s[i+2]??''))return {end:i+2,tex:'E_{\\text{đ}}',kind:'variable'};
  const word=starts(s,i,/^[A-Za-zΔΦφλρηωαβγθμπσετΩν]+(?:\d+[A-Za-zΔΦφλρηωαβγθμπσετΩν]*)*/u);
  if(!word)return null;
  let raw=word[0],end=i+raw.length;
  const embedded=raw.slice(1).search(/sin|cos|tan|ln|log/);if(embedded>=0){raw=raw.slice(0,embedded+1);end=i+raw.length;}
  if(letter.test(s[end]??'')&&s[end]!=='̄'&&!/^(?:sin|cos|tan|ln|log)/.test(s.slice(end)))return null;
  if(!(/^[A-Za-zΔΦφλρηωαβγθμπσετΩν]\d*$/u.test(raw)||(/.[A-ZΔΦφλρηωαβγθμπσετΩν]/u.test(raw)||/^[A-Z]{1,5}$/.test(raw)||/[ΔΦφλρηωαβγθμπσετΩν]/u.test(raw))&&raw.length<=16||/^(?:[A-Za-zΔΦφλρηωαβγθμπσετΩν]\d+){2,}[A-Za-zΔΦφλρηωαβγθμπσετΩν]?$/u.test(raw)||/^(?:mc|mv|mn|mp|md|mg|dh|Bl|Br|Blv|Dg|Lm|Ze|rms|sin|cos|tan|ln|log|const)$/u.test(raw)||s[end]==='_'))return null;
  let t=raw==='NA'?'N_{A}':raw.replace(/([A-Za-zΔΦφλρηωαβγθμπσετΩν])(\d+)/gu,'$1_{$2}');
  t=t.replace(/[ΔΦφλρηωαβγθμπσετΩν]/gu,c=>'\\'+greek[c]+' ');
  if(/^(?:sin|cos|tan|ln|log)$/.test(raw))t='\\'+raw+' ';
  if(raw==='const')t=roman(raw);
  const unicode=starts(s,end,/^[₀₁₂₃₄₅₆₇₈₉₊₋]+/u);
  if(unicode){t+='_{'+digits(unicode[0],sub)+'}';end+=unicode[0].length;}
  if(s[end]==='_'){
   let label=null;
   for(const candidate of named){if(s.startsWith(candidate,end+1)){label=candidate;break;}}
   if(label){end+=1+label.length;t+='_{'+text(label)+'}';}
   else {
    const m=starts(s,end+1,/^(?:\{([^{}]+)\}|([\p{L}\p{M}\d]+))/u);
    if(m){const v=m[1]??m[2];end+=1+m[0].length;t+='_{'+(/^\d+$/.test(v)?v:/^[A-Za-z]{1,3}$/.test(v)?roman(v):text(v))+'}';}
    else return null;
   }
  }
  const label=starts(s,end,/^ (riêng|điện|nhiệt|phân rã|hạt nhân|mỗi phân hạch|phân hạch)(?![\p{L}])/u);
  if(label&&/[WEPm]$/.test(raw)&&!t.includes('_{')){t+='_{'+text(label[1])+'}';end+=label[0].length;}
  if(s[end]==='̄'){t='\\overline{'+t+'}';end++;}
  return {end,tex:t,kind:'variable'};
 }
 function isotope(s,i,nuclear){
  let m=starts(s,i,/^([A-Z][a-z]?)[-–](\d{1,3})(?![\p{L}\d])/u),elem,mass,end;
  if(m){elem=m[1];mass=+m[2];end=i+m[0].length;}
  else {
   m=starts(s,i,/^(\d{1,3})([A-Z][a-z]?)(?![\p{L}\d_])/u);
   if(!m)return null;
   elem=m[2];mass=+m[1];end=i+m[0].length;
   // Compact Coulomb/Henry/tesla quantities require explicit nuclear context.
   if(units.includes(elem)&&!nuclear)return null;
  }
  if(!elements[elem]||mass<elements[elem]||mass>Math.min(300,3*elements[elem]+10))return null;
  return {end,tex:'{}^{'+mass+'}'+roman(elem),kind:'isotope'};
 }
 function atom(s,i,ctx,depth=0){
  if(depth>16)return null;
  const fn=starts(s,i,/^(sin|cos|tan|ln|log)(?=[\d\s(ΔΦφλρηωαβγθμπσετΩν])/u);
  let a=fn?{end:i+fn[0].length,tex:'\\'+fn[0]+' ',kind:'function'}:isotope(s,i,ctx.nuclear)||number(s,i);
  if(a&&a.kind==='number'){
   const e=exponent(s,a.end);if(e){a.end=e.end;a.tex+=e.tex;}
   const ws=starts(s,a.end,/^\s*/)[0],u=unit(s,a.end+ws.length);
   if(u&&!(s.slice(a.end+ws.length,u.end)==='T'&&(ctx.halfLife||!ws&&!ctx.magnetic))){a={end:u.end,tex:a.tex+'\\,'+u.tex,numericTex:a.tex,unitTex:u.tex,kind:'quantity'};}
  }
  if(!a&&s[i]==='('){
   const u=unit(s,i+1);
   if(u&&s[u.end]===')')a={end:u.end+1,tex:'('+u.tex+')',inner:u.tex,kind:'group'};
   else {
    const expr=expression(s,i+1,ctx,depth+1);
    if(expr&&s[expr.end]===')')a={end:expr.end+1,tex:'('+expr.tex+')',inner:expr.tex,kind:'group'};
   }
  }
  if(!a&&s[i]==='|'){
   const inner=expression(s,i+1,ctx,depth+1);if(inner&&s[inner.end]==='|')a={end:inner.end+1,tex:'\\lvert '+inner.tex+'\\rvert ',kind:'group'};
  }
  if(!a&&s[i]==='√'){
   const ws=starts(s,i+1,/^\s*/)[0];const inner=atom(s,i+1+ws.length,ctx,depth+1);
   if(inner)a={end:inner.end,tex:'\\sqrt{'+(inner.inner??inner.tex)+'}',kind:'root'};
  }
  if(!a&&s[i]==='⟨'){
   const inner=expression(s,i+1,ctx,depth+1);
   if(inner&&s[inner.end]==='⟩')a={end:inner.end+1,tex:'\\langle '+inner.tex+'\\rangle ',kind:'group'};
  }
  if(!a&&s[i]==='\\'){
   const command=starts(s,i,/^\\(?:[A-Za-z]+|[%#$&_{}])/);
   if(command){
    let end=i+command[0].length;
    for(let n=0;n<4;n++){
     const ws=starts(s,end,/^\s*/)[0],at=end+ws.length;if(s[at]!=='{'&&s[at]!=='[')break;
     const close=s[at]==='{'?'}':']';let level=1,j=at+1;
     while(j<s.length&&level){if(s[j]==='\\'){j+=2;continue;}if(s[j]===s[at])level++;if(s[j]===close)level--;j++;}
     if(level)break;end=j;
    }
    a={end,tex:s.slice(i,end),kind:'tex'};
   }
  }
  if(!a){const u=unit(s,i);if(u&&s.slice(i,u.end)!=='W/A'&&(ctx.unit||/[\/⁰¹²³⁴⁵⁶⁷⁸⁹^°%]/u.test(s.slice(i,u.end))))a=u;}
  if(!a)a=variable(s,i);
  if(!a&&(ctx.unit||s[i]==='°'||s[i]==='%'))a=unit(s,i);
  if(!a)return null;
  if(a.kind==='group'&&s.startsWith(' mỗi vòng',a.end)){a.tex+='_{'+text('mỗi vòng')+'}';a.end+=9;}
  if(a.kind==='tex'&&s[a.end]==='_'){
   const script=starts(s,a.end+1,/^(?:\{[^{}]+\}|[+\-]?\d+|[A-Za-z])/);
   if(script){a.tex+='_{'+script[0].replace(/^\{|\}$/g,'')+'}';a.end+=1+script[0].length;}
  }
  const e=exponent(s,a.end);if(e){a={...a,end:e.end,tex:a.tex+e.tex};delete a.inner;}
  return a;
 }
 const ops={'×':'\\times ','*':'\\cdot ','·':'\\cdot ','⋅':'\\cdot ','≤':'\\le ','≥':'\\ge ','≠':'\\ne ','≈':'\\approx ','≃':'\\simeq ','∝':'\\propto ','→':'\\to ','⇒':'\\Rightarrow ','↔':'\\leftrightarrow ','±':'\\pm ','−':'-','<':'\\lt ','>':'\\gt '};
 function expression(s,i,ctx,depth=0){
  let end=i,nodes=[],pending='';
  const sign=starts(s,end,ctx.unit?/^[+\-−×]/u:/^[+\-−]/u);if(sign){pending=sign[0]==='×'?'\\times ':sign[0].replace(/−/g,'-');end++;}
  let first=atom(s,end,ctx,depth);if(!first)return null;
  nodes.push({...first,...(first.inner?{inner:pending+first.inner}:{}),tex:pending+first.tex});end=first.end;
  for(let count=0;count<150;count++){
   const ws=starts(s,end,/^\s*/)[0],at=end+ws.length;
   const asciiTimes=/^[xX]\s*(?=10(?:\^|[⁰¹²³⁴⁵⁶⁷⁸⁹]))/u.test(s.slice(at))&&/^(?:number|quantity)$/.test(nodes[nodes.length-1].kind);
   const op=asciiTimes?['×']:starts(s,at,/^[=+\-−*/×·⋅≤≥≠≈≃∝→⇒↔±<>]/u);
   let nextAt=at,operator='';
   if(op){operator=op[0];const after=at+1;nextAt=after+starts(s,after,/^\s*/)[0].length;}
   let sign='';
   if(operator&&/^[+\-−]/.test(s.slice(nextAt))){sign=s[nextAt].replace(/−/g,'-');nextAt++;}
   let next=atom(s,nextAt,ctx,depth);
   if(!next&&operator&&s.startsWith('hằng số',nextAt)){next={end:nextAt+7,tex:text('hằng số'),kind:'constant'};}
   if(!next)break;
   // Spaces between mathematical atoms are allowed; words must be complete atoms.
   if(!operator&&!ws&&nextAt===end&&nodes[nodes.length-1].kind!=='function'&&letter.test(s[end-1]??'')&&letter.test(s[end]??''))break;
   if(operator==='/'){
    const prev=nodes.pop();
    if((prev.kind==='number'||prev.numericFraction)&&next.kind==='quantity'){
     nodes.push({kind:'quantity',tex:'\\frac{'+prev.tex+'}{'+sign+next.numericTex+'}\\,'+next.unitTex});
    }else nodes.push({kind:'fraction',numericFraction:prev.kind==='number'&&next.kind==='number',tex:'\\frac{'+(prev.inner??prev.tex)+'}{'+sign+(next.inner??next.tex)+'}'});
   }else {if(operator)nodes.push({kind:'operator',tex:ops[operator]??operator});nodes.push({...next,tex:sign+next.tex});}
   end=next.end;
  }
  return {end,tex:nodes.map(n=>n.tex).join(' '),kind:'expression'};
 }
 function plain(s,kind){
  const result=[],ctx={unit:kind==='unit',halfLife:/bán rã|phóng xạ|phân rã|hạt nhân|hoạt độ|ngày|giờ/iu.test(s),magnetic:/cảm ứng từ|từ trường|tesla|\bB(?:_?\d)?\s*[=≈]/iu.test(s),nuclear:/hạt nhân|đồng vị|phóng xạ|phân hạch|isotope|nuclear/iu.test(s)};
  const trimmed=s.trim(),allUnit=unit(trimmed,0);
  if(allUnit&&allUnit.end===trimmed.length&&trimmed!=='W/A'&&(kind==='unit'||!/^[A-Z]\d+$/.test(trimmed)))return [{kind:'math',tex:allUnit.tex}];
  let textStart=0,i=0;
  while(i<s.length){
   if(s.startsWith('@@',i)){const close=s.indexOf('@@',i+2);if(close>=0){i=close+2;continue;}}
   if(i>0&&(letter.test(s[i-1])||/[\d_]/.test(s[i-1]))){i++;continue;}
   const e=expression(s,i,ctx);
   if(!e){i++;continue;}
   if(i>textStart)result.push({kind:'text',text:s.slice(textStart,i)});
   result.push({kind:'math',tex:e.tex});i=e.end;textStart=i;
  }
  if(textStart<s.length)result.push({kind:'text',text:s.slice(textStart)});
  return result;
 }
 function segments(s,kind){
  const result=[];let cursor=0;
  // Explicit TeX stays intact; it never re-enters the automatic prose parser.
  const re=/\\\(([\s\S]*?)\\\)|\\\[([\s\S]*?)\\\]|\$\$([\s\S]*?)\$\$|(?<!\\)\$([^$\n]+)(?<!\\)\$/g;
  for(const m of s.matchAll(re)){
   result.push(...plain(s.slice(cursor,m.index),kind));
   result.push({kind:m[2]!==undefined||m[3]!==undefined?'display':'math',tex:m[1]??m[2]??m[3]??m[4]});cursor=m.index+m[0].length;
  }
  result.push(...plain(s.slice(cursor),kind));return result;
 }
 function html(s,kind){return segments(s,kind).map(n=>n.kind==='text'?escape(n.text):n.kind==='display'?'\\['+escape(n.tex)+'\\]':'\\('+escape(n.tex)+'\\)').join('');}
 function tex(s){const e=expression(s.trim(),0,{unit:false,nuclear:/hạt nhân|đồng vị|phóng xạ|phân hạch|isotope|nuclear/iu.test(s)});return e&&e.end===s.trim().length?e.tex:s;}
 return {html,tex,segments};
})();
let phyMathQueue=Promise.resolve();
function typesetMath(el){
 // Serialize dynamic views with MathJax startup and with one another.
 phyMathQueue=phyMathQueue.then(async()=>{
  const mj=window.MathJax;if(!mj)return;
  if(mj.startup&&mj.startup.promise)await mj.startup.promise;
  if(mj.typesetPromise)await mj.typesetPromise(el?[el]:undefined);
 }).catch(error=>{console.error('Math typesetting failed',error);});
 return phyMathQueue;
}
'''

HOOKS = r'''
<!-- PHY_AI_LATEX_UNIFIED_V3 -->
<script>
(()=>{
 const views={renderQuestion:'questionView',renderRepair:'repairView',renderExamQuestion:'examView',submitCurrentAnswer:'qFeedback',submitRepair:'repairFeedback',startRepair:'repairView',submitExam:'examResultView'};
 for(const [name,id] of Object.entries(views)){
  const original=window[name];
  if(typeof original!=='function')throw new Error('Missing math rendering path: '+name);
  window[name]=function(...args){
   const el=document.getElementById(id);
   if(window.MathJax&&MathJax.typesetClear&&el)MathJax.typesetClear([el]);
   const value=original.apply(this,args);
   if(value&&typeof value.then==='function')return value.then(result=>typesetMath(el).then(()=>result));
   typesetMath(el);return value;
  };
 }
})();
</script>
'''


def apply_patch(root='/app'):
    frontend = Path(root) / 'app/static/index.html'
    html = frontend.read_text(encoding='utf-8')
    if MARKER in html:
        assert html.count(MARKER) == 1, 'Duplicate unified math renderer'
        assert 'const phyMath=' in html and 'legacyMathHtml' not in html
        assert 'mathjax@3.2.2/es5/tex-chtml.js' in html, 'MathJax version drift'
        return False
    # Remove the superseded appended wrapper, including both legacy marker names.
    html = re.sub(r'\s*<!-- PHY_AI_LATEX_STANDARD_V[12] -->\s*<script>[\s\S]*?</script>', '', html)
    start = html.find('function texCore(')
    end = html.find('async function api(', start)
    assert start >= 0 and end > start, 'Base math helper markers missing'
    assert html[start:end].count('function mathHtml(') == 1, 'Unexpected math helper block'
    html = html[:start] + RENDERER + '\n' + html[end:]
    html = html.replace('mathjax@3/es5/tex-chtml.js', 'mathjax@3.2.2/es5/tex-chtml.js')
    assert 'mathjax@3.2.2/es5/tex-chtml.js' in html, 'MathJax script marker missing'
    html = html.replace("mathHtml(q.unit||'')", "mathHtml(q.unit||'','unit')")
    assert html.count('</body>') == 1, 'Frontend body marker missing or duplicated'
    for name in ['renderQuestion', 'renderRepair', 'renderExamQuestion', 'submitCurrentAnswer', 'submitRepair', 'startRepair', 'submitExam']:
        assert re.search(r'function\s+' + name + r'\(', html), 'Rendering path missing: ' + name
    html = html.replace('</body>', HOOKS + '\n</body>', 1)
    assert 'legacyMathHtml' not in html and 'const hold=' not in html
    assert html.count(MARKER) == 1
    frontend.write_text(html, encoding='utf-8')
    return True


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', default='/app')
    apply_patch(parser.parse_args().root)
