"""Audit question stems for formulas already taught in the Physics 12 textbook."""

import re
import app.main as m

PATTERNS = {
    "first_law": r"(?:ΔU|\\Delta U)\s*=\s*A\s*[+\-]\s*Q",
    "temp_c_to_k": r"T\s*\(?K\)?\s*[≈=]\s*t\s*\(?°?C\)?\s*\+\s*27[3]\b",
    "temp_k_to_c": r"t\s*\(?°?C\)?\s*[≈=]\s*T\s*\(?K\)?\s*[-−]\s*27[3]\b",
    "heat": r"Q\s*=\s*m\s*c\s*(?:ΔT|\\Delta T)",
    "fusion": r"(?:Q\s*=\s*m\s*λ|λ\s*=\s*Q\s*/\s*m)",
    "vapor": r"(?:Q\s*=\s*m\s*L|L\s*=\s*Q\s*/\s*m)",
    "boyle": r"(?:p\s*V\s*=\s*hằng\s*số|p\s*1\s*V\s*1\s*=\s*p\s*2\s*V\s*2)",
    "charles": r"(?:V\s*/\s*T\s*=\s*hằng\s*số|V\s*1\s*/\s*T\s*1\s*=\s*V\s*2\s*/\s*T\s*2)",
    "gas_state": r"p\s*1\s*V\s*1\s*/\s*T\s*1\s*=\s*p\s*2\s*V\s*2\s*/\s*T\s*2",
    "clapeyron": r"p\s*V\s*=\s*n\s*R\s*T",
    "kinetic_pressure": r"p\s*=\s*(?:1\s*/\s*3|2\s*/\s*3).{0,25}(?:v|E|ρ|mu|μ)",
    "kinetic_energy": r"(?:Ē|E_bar|E)\s*=\s*3\s*/\s*2\s*k\s*T",
    "magnetic_force": r"F\s*=\s*B\s*I\s*[lL]\s*(?:sin|\\sin)",
    "flux": r"(?:Φ|Phi)\s*=\s*B\s*S\s*(?:cos|\\cos)",
    "faraday": r"(?:e[_ ]?c|e_c)\s*=\s*-?\s*N?\s*(?:ΔΦ|\\Delta\s*Φ|dΦ).{0,12}/.{0,8}(?:Δt|dt)",
    "ac_voltage": r"u\s*=\s*U\s*0\s*(?:cos|\\cos)",
    "ac_current": r"i\s*=\s*I\s*0\s*(?:cos|\\cos)",
    "rms_current": r"I\s*=\s*I\s*0\s*/\s*(?:√\s*2|sqrt\s*2)",
    "rms_voltage": r"U\s*=\s*U\s*0\s*/\s*(?:√\s*2|sqrt\s*2)",
    "transformer": r"U\s*1\s*/\s*U\s*2\s*=\s*N\s*1\s*/\s*N\s*2",
    "em_wave": r"λ\s*=\s*c\s*(?:T|/\s*f)",
    "mass_energy": r"E\s*=\s*m\s*c\s*(?:²|\^\s*2)",
    "mass_defect": r"Δm\s*=\s*\[?\s*Z.{0,45}(?:mX|m_X)",
    "binding": r"E[_ ]?lk\s*=\s*Δm\s*c",
    "binding_per_nucleon": r"E[_ ]?lkr\s*=\s*E[_ ]?lk\s*/\s*A",
    "decay": r"N[_ ]?[tₜ]\s*=\s*N[_ ]?0\s*(?:2|e).{0,20}(?:t|λ)",
    "activity": r"(?:H|A)[_ ]?[tₜ]?\s*=\s*λ\s*N",
}

violations=[]
for q in m.bank.questions:
    prompt=str(q.get("prompt") or "")
    normalized=prompt.replace("₀","0").replace("₁","1").replace("₂","2")
    for name,pattern in PATTERNS.items():
        if re.search(pattern,normalized,re.I):
            violations.append((q["id"],name,prompt))
            break

print("SGK_FORMULA_STEM_VIOLATIONS",len(violations))
for qid,name,prompt in violations:
    print(f"FORMULA_LEAK|{qid}|{name}|{prompt}")
