from pathlib import Path

p = Path('/app/app/static/index.html')
html = p.read_text(encoding='utf-8')

marker = '<!-- PHY_AI_LATEX_STANDARD_V2 -->'
if marker not in html:
    script = r'''
<!-- PHY_AI_LATEX_STANDARD_V1 -->
<script>
(function(){
  const legacyMathHtml = window.mathHtml;

  const supMap={'⁰':'0','¹':'1','²':'2','³':'3','⁴':'4','⁵':'5','⁶':'6','⁷':'7','⁸':'8','⁹':'9','⁺':'+','⁻':'-'};
  const subMap={'₀':'0','₁':'1','₂':'2','₃':'3','₄':'4','₅':'5','₆':'6','₇':'7','₈':'8','₉':'9','₊':'+','₋':'-'};

  const baseUnits = [
    'MeV','keV','GeV','MHz','kHz','GHz','mmHg','kPa','MPa','GPa','kJ','MJ','mJ','μJ',
    'mW','kW','MW','mV','kV','mA','μA','mT','mWb','kΩ','MΩ',
    'nm','μm','mm','cm','dm','km','mg','μg','kg','ms','μs','ns',
    'mol','rad','sr','Hz','Pa','atm','bar','eV','J','N','W','C','V','A','T','K','Wb','Ω',
    'Bq','Gy','Sv','u','g','m','s','L','mL','dB','%',
    'J/kg','J/(kg.K)','J/(kg·K)','J/(kg K)','W/(m.K)','W/(m·K)','N/A','N/(A.m)','N/(A·m)',
    'kg/m3','kg/m^3','kg/m³','m/s','m/s2','m/s^2','m/s²','m2','m^2','m²','m3','m^3','m³',
    'C/kg','J/mol','J/(mol.K)','J/(mol·K)','Pa.s','Pa·s','N.m','N·m','V/m','A/m','W/m2','W/m^2','W/m²'
  ].sort((a,b)=>b.length-a.length);

  const unitAtom = '(?:' + baseUnits.map(u=>u.replace(/[.*+?^$()|[\]\\{}]/g,'\\$&')).join('|') + ')';
  const exp = '(?:\\^?[+\\-]?\\d+|[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)?';
  const atomExp = unitAtom + exp;
  const unitExprSource = atomExp + '(?:\\s*(?:[·⋅.]|\\/|\\s)\\s*' + atomExp + ')*';
  const unitExprFull = new RegExp('^\\s*' + unitExprSource + '\\s*$','u');
  const quantityRe = new RegExp(
    '([+\\-−]?\\d+(?:[.,]\\d+)?(?:\\s*(?:×|x|X|\\\\*)\\s*10(?:\\s*\\^?\\s*[+\\-−]?\\d+|[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+))?)\\s*(' + unitExprSource + ')(?=$|[\\s,;:.!?\\)])',
    'gu'
  );

  function superscriptDigits(s){
    return [...s].map(c=>supMap[c] ?? c).join('');
  }
  function subscriptDigits(s){
    return [...s].map(c=>subMap[c] ?? c).join('');
  }
  function latexNumber(raw){
    let s=String(raw).trim().replace(/−/g,'-');
    s=s.replace(/([0-9]),(?=[0-9])/g,'$1{,}');
    s=s.replace(/([+\-]?\d+(?:\{,\}\d+|\.\d+)?)\s*(?:×|x|X|\*)\s*10\s*(?:\^?\s*([+\-]?\d+)|([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+))/u,
      (_,a,b,c)=>a+'\\times 10^{'+(b||superscriptDigits(c||''))+'}');
    s=s.replace(/([+\-]?\d+(?:\{,\}\d+|\.\d+)?)[eE]([+\-]?\d+)/g,'$1\\times 10^{$2}');
    return s;
  }
  function unitAtomTex(raw, denominator=false){
    let s=String(raw).trim();
    if(s==='%') return '\\%';
    let exponent='';
    let m=s.match(/([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)$/u);
    if(m){ exponent=superscriptDigits(m[1]); s=s.slice(0,-m[1].length); }
    else {
      m=s.match(/\^([+\-]?\d+)$/);
      if(m){ exponent=m[1]; s=s.slice(0,-m[0].length); }
      else {
        m=s.match(/^(.*?)([+\-]?\d+)$/);
        if(m && baseUnits.includes(m[1])){ s=m[1]; exponent=m[2]; }
      }
    }
    if(denominator){
      if(exponent) exponent=String(-Number(exponent));
      else exponent='-1';
    }
    let out='\\mathrm{'+s.replace(/Ω/g,'\\Omega ')+'}';
    if(exponent) out+='^{'+exponent+'}';
    return out;
  }
  function unitToTex(raw){
    let s=String(raw).trim().replace(/⋅/g,'·').replace(/\.K\b/g,'·K').replace(/\.m\b/g,'·m').replace(/\.s\b/g,'·s');
    s=s.replace(/\(([^()]*)\)/g,'$1');
    if(s==='°C' || s==='℃') return '^{\\circ}\\mathrm{C}';
    if(s==='°') return '^{\\circ}';
    if(s==='%') return '\\%';

    const slash=s.indexOf('/');
    let num=s, den='';
    if(slash>=0){ num=s.slice(0,slash); den=s.slice(slash+1); }
    den=den.replace(/^\s*\(|\)\s*$/g,'');

    const splitPart=(part,denom)=>part
      .split(/\s*(?:[·.]|\s)\s*/u)
      .filter(Boolean)
      .map(x=>unitAtomTex(x,denom))
      .join('\\,');

    const n=splitPart(num,false);
    const d=den?splitPart(den,true):'';
    return d ? (n ? n+'\\,'+d : d) : n;
  }
  function isUnitExpr(s){
    const t=String(s).trim();
    return t==='°C'||t==='℃'||t==='°'||unitExprFull.test(t);
  }
  function quantityToTex(num,unit){
    const u=unitToTex(unit);
    return latexNumber(num) + (u ? '\\,'+u : '');
  }

  function standardTexCore(x){
    let s=String(x??'').trim();
    if(!s) return s;

    s=s.replace(/−/g,'-')
       .replace(/Ē/g,'\\overline{E}')
       .replace(/⟨/g,'\\langle ').replace(/⟩/g,'\\rangle ')
       .replace(/≈/g,'\\approx ').replace(/≃/g,'\\simeq ')
       .replace(/≠/g,'\\ne ').replace(/≤/g,'\\le ').replace(/≥/g,'\\ge ')
       .replace(/±/g,'\\pm ').replace(/∞/g,'\\infty ')
       .replace(/→/g,'\\to ').replace(/↔/g,'\\leftrightarrow ')
       .replace(/×/g,'\\times ').replace(/[·⋅]/g,'\\cdot ');

    s=s.replace(/([A-Za-z0-9)\]])([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)/gu,
      (_,b,e)=>b+'^{'+superscriptDigits(e)+'}');
    s=s.replace(/([A-Za-z])([₀₁₂₃₄₅₆₇₈₉₊₋]+)/gu,
      (_,b,e)=>b+'_{'+subscriptDigits(e)+'}');
    s=s.replace(/\^\(([^)]+)\)/g,'^{$1}')
       .replace(/\^([+\-]?\d+|[A-Za-z])/g,'^{$1}');

    s=s.replace(/([A-Za-z])_([A-Za-zÀ-ỹ][A-Za-zÀ-ỹ ]*)/gu,
      (_,a,b)=>a+'_{\\mathrm{'+b.trim().replace(/\s+/g,'\\,')+'}}');
    s=s.replace(/\bNA\b/g,'N_A');

    const greek={'Δ':'\\Delta ','Φ':'\\Phi ','φ':'\\varphi ','λ':'\\lambda ','ρ':'\\rho ','η':'\\eta ','ω':'\\omega ','α':'\\alpha ','β':'\\beta ','γ':'\\gamma ','θ':'\\theta ','μ':'\\mu ','π':'\\pi ','σ':'\\sigma ','ε':'\\varepsilon ','τ':'\\tau '};
    s=s.replace(/[ΔΦφλρηωαβγθμπσετ]/g,c=>greek[c]||c);

    s=s.replace(/√\s*\(([^)]+)\)/g,'\\sqrt{$1}')
       .replace(/√\s*([A-Za-z0-9]+)/g,'\\sqrt{$1}');
    s=s.replace(/\b([0-9]{1,3})\s*([A-Z][a-z]?)\b/g,'{}^{$1}\\mathrm{$2}');
    s=s.replace(/\bsin\s*/g,'\\sin ').replace(/\bcos\s*/g,'\\cos ')
       .replace(/\btan\s*/g,'\\tan ').replace(/\bln\s*/g,'\\ln ')
       .replace(/\blog\s*/g,'\\log ');

    s=s.replace(/°C/g,'^{\\circ}\\mathrm{C}').replace(/℃/g,'^{\\circ}\\mathrm{C}').replace(/°/g,'^{\\circ}');
    s=s.replace(/(\d),(?=\d)/g,'$1{,}');

    s=s.replace(/(^|[=+\-(\s])([+\-]?\d+)\s*\/\s*(\d+)(?=[$+\-*/)\sA-Za-zΔΦλρηωαβγθμπσετ])/g,
      (_,p,a,b)=>p+'\\frac{'+a+'}{'+b+'}');

    return s.replace(/\s+/g,' ').trim();
  }

  window.texCore = standardTexCore;

  window.mathHtml = function(value){
    const raw0=String(value??'');
    if(!raw0) return '';

    if(isUnitExpr(raw0)){
      return '\\('+unitToTex(raw0)+'\\)';
    }

    let held=[];
    const hold=tex=>{
      const key='@@U'+held.length+'@@';
      held.push('\\('+tex+'\\)');
      return key;
    };

    let raw=raw0;

    raw=raw.replace(/([+\-−]?\d+(?:[.,]\d+)?)\s*(?:°\s*C|℃)/gu,
      (_,n)=>hold(latexNumber(n)+'\\,^{\\circ}\\mathrm{C}'));

    raw=raw.replace(quantityRe,(m,n,u)=>hold(quantityToTex(n,u)));

    // Common SI compound units written in textbook style, e.g. kg/m³, J/(kg·K), m/s².
    raw=raw.replace(/\b(J\s*\/\s*\(?\s*kg\s*[·.]?\s*K\s*\)?|W\s*\/\s*\(?\s*m\s*[·.]?\s*K\s*\)?|kg\s*\/\s*m(?:\^?3|³)|m\s*\/\s*s(?:\^?2|²)|m\s*\/\s*s|N\s*\/\s*\(?\s*A\s*[·.]?\s*m\s*\)?|W\s*\/\s*m(?:\^?2|²)|J\s*\/\s*kg|J\s*\/\s*mol)\b/gu,
      m=>hold(unitToTex(m.replace(/\s+/g,''))));

    raw=raw.replace(/\(([^()]{1,28})\)/gu,(m,u)=>isUnitExpr(u)?'('+hold(unitToTex(u))+')':m);

    raw=raw.replace(/\\\((.+?)\\\)/gs,(_,x)=>hold(standardTexCore(x)));
    raw=raw.replace(/\\\[(.+?)\\\]/gs,(_,x)=>hold(standardTexCore(x)));
    raw=raw.replace(/\$([^$\n]+)\$/g,(_,x)=>hold(standardTexCore(x)));

    let out = legacyMathHtml ? legacyMathHtml(raw) : esc(raw);
    out=out.replace(/@@U(\d+)@@/g,(_,i)=>held[Number(i)]||'');
    return out;
  };

  const oldTypeset=window.typesetMath;
  window.typesetMath=function(el){
    if(oldTypeset) return oldTypeset(el);
    if(window.MathJax&&MathJax.typesetPromise) MathJax.typesetPromise(el?[el]:undefined).catch(()=>{});
  };
})();
</script>
'''
    html = html.replace('</body>', script + '\n</body>', 1)

p.write_text(html, encoding='utf-8')
