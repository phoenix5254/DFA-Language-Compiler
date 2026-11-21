# Flask handles the browser page and the request sent when the user runs the compiler.
from flask import Flask, render_template_string, request, jsonify
from pathlib import Path
import re

app = Flask(__name__)

# The page is kept here so the project can be started with one command.
PAGE = r"""
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DFA-Language-Compiler | Compiler Studio</title>
<style>
/* Main colours for the dark, warm-toned workspace. */
:root{--bg:#171515;--panel:#211d1c;--panel2:#2b2523;--line:#403633;--text:#f4efeb;--muted:#b8aaa2;--cyan:#c94b45;--lime:#d8b65b;--red:#e45b55;--amber:#c9a45a}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 12% 0%,#30201f 0,#171515 48%);color:var(--text);font:15px/1.5 Inter,Segoe UI,Arial,sans-serif}
header{display:flex;justify-content:space-between;align-items:center;padding:20px 4vw;border-bottom:1px solid var(--line);background:#171515ed;position:sticky;top:0;z-index:2;backdrop-filter:blur(12px)}
.brand{font-size:21px;font-weight:800;letter-spacing:.4px}.brand span{color:var(--cyan)}.tag{color:var(--muted);font-size:12px}
.wrap{max-width:1500px;margin:auto;padding:26px 4vw}.hero{display:flex;justify-content:space-between;gap:20px;align-items:end;margin-bottom:20px}.hero h1{font-size:30px;margin:0 0 5px}.hero p{margin:0;color:var(--muted)}
.actions{display:flex;gap:9px;flex-wrap:wrap}button,.filebtn{border:1px solid var(--line);background:var(--panel2);color:var(--text);padding:10px 15px;border-radius:10px;font-weight:650;cursor:pointer}button.primary{background:#c94b45;color:#fff8f4;border:1px solid #c94b45}button:hover,.filebtn:hover{filter:brightness(1.15)}
.grid{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(380px,.9fr);gap:18px}.panel{background:linear-gradient(160deg,#25201f,#1d1a19);border:1px solid var(--line);border-radius:17px;overflow:hidden;box-shadow:0 16px 40px #0003}.panelhead{padding:14px 17px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center}.panelhead strong{font-size:14px}.pill{font-size:11px;padding:4px 9px;border-radius:99px;background:#39302b;color:#d8c5ae}
textarea{width:100%;min-height:510px;resize:vertical;background:#171515;color:#eee6e0;border:0;outline:0;padding:20px;font:13px/1.75 Consolas,Monaco,monospace;tab-size:4;white-space:pre;overflow:auto}
.right{display:grid;grid-template-rows:auto minmax(300px,1fr) auto;gap:14px}.status{padding:14px 17px;color:var(--muted);min-height:75px}.status.good{color:var(--lime)}.status.bad{color:var(--red)}.status h3{margin:0 0 4px;font-size:15px}.status p{margin:0}
#diagram{width:100%;height:100%;min-height:330px;background:radial-gradient(circle at center,#302523,#171515);display:block}
.errors{padding:12px 16px 16px;border-top:1px solid var(--line);max-height:220px;overflow:auto}.err{padding:9px 11px;margin:7px 0;border:1px solid #75413d;background:#30201f;border-radius:9px;color:#f1dfd8;font:12px/1.5 Consolas,monospace}.err b{color:#f08b7e}.hint{color:var(--muted);font-size:12px;padding:13px 17px}.footer{color:var(--muted);font-size:12px;margin-top:16px}
@media(max-width:900px){.grid{grid-template-columns:1fr}.hero{display:block}.actions{margin-top:15px}textarea{min-height:360px}}
</style></head><body>
<header><div><div class="brand">DFA-Language-Compiler <span style="color:#f4efeb">/ Compiler Studio</span></div><div class="tag">Formal DFA descriptions, validation and state diagrams</div></div><div class="tag">CIT4004 · APL Project</div></header>
<main class="wrap"><section class="hero"><div><h1>DFA-Language-Compiler</h1><p>Write, validate and visualize deterministic finite automata.</p></div>
<div class="actions"><button onclick="loadExample()">Load valid example</button><label class="filebtn">Open .txt<input id="file" type="file" accept=".txt,text/plain" hidden onchange="openFile(event)"></label><button onclick="saveSource()">Save source</button><button class="primary" onclick="compileCode()">▶ Run compiler</button></div></section>
<div class="grid"><section class="panel"><div class="panelhead"><strong>01 / SOURCE EDITOR</strong><span class="pill">DFA language</span></div>
<textarea id="source" spellcheck="false">M = (Q, Σ, δ, q0, F)
Q = {q1, q2, q3, q4, Trap}
Σ = {a, b, c}
δ = Q X Σ -> Q
q0 = q1
F = {q4}
δ a b c
q1 q2 q3 Trap
q2 q4 Trap q2
q3 Trap q4 q3
q4 Trap Trap Trap
Trap Trap Trap Trap</textarea>
<div class="hint">Tip: use the supplied examples to test valid and invalid DFA descriptions.</div></section>
<div class="right"><section class="panel"><div class="panelhead"><strong>02 / COMPILER STATUS</strong><span id="badge" class="pill">READY</span></div><div id="status" class="status"><h3>Ready to compile</h3><p>Press Run compiler to start lexical, syntax and semantic analysis.</p></div><div id="errors" class="errors" style="display:none"></div></section>
<section class="panel"><div class="panelhead"><strong>03 / DFA STATE DIAGRAM</strong><span class="pill">SVG renderer</span></div><svg id="diagram" viewBox="0 0 760 430" role="img" aria-label="DFA diagram"><text x="380" y="210" fill="#b8aaa2" text-anchor="middle" font-size="16">Your validated DFA will appear here</text></svg></section></div></div>
<div class="footer">Compiler stages: Lexer → Parser → Semantic Analyzer → DFA Renderer. Diagram is shown only when validation succeeds.</div></main>
<script>
const validExample=`M = (Q, Σ, δ, q0, F)
Q = {q1, q2, q3, q4, Trap}
Σ = {a, b, c}
δ = Q X Σ -> Q
q0 = q1
F = {q4}
δ a b c
q1 q2 q3 Trap
q2 q4 Trap q2
q3 Trap q4 q3
q4 Trap Trap Trap
Trap Trap Trap Trap`;
// Put the built-in sample back in the editor.
function loadExample(){document.getElementById('source').value=validExample}
// Read a local text file without sending it anywhere until Compile is clicked.
function openFile(e){const f=e.target.files[0];if(!f)return;const r=new FileReader();r.onload=()=>document.getElementById('source').value=r.result;r.readAsText(f)}
// Let the user keep a copy of the DFA they are editing.
function saveSource(){const blob=new Blob([document.getElementById('source').value],{type:'text/plain'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='my_dfa.txt';a.click();URL.revokeObjectURL(a.href)}
// Send the source to Flask and show the response from the compiler stages.
async function compileCode(){const status=document.getElementById('status'),badge=document.getElementById('badge'),errors=document.getElementById('errors');status.className='status';status.innerHTML='<h3>Compiling…</h3><p>Running lexical, syntax and semantic analysis.</p>';badge.textContent='RUNNING';errors.style.display='none';document.getElementById('diagram').innerHTML='<text x="380" y="210" fill="#b8aaa2" text-anchor="middle">Waiting for successful validation…</text>';
try{const res=await fetch('/compile',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({source:document.getElementById('source').value})});const contentType=res.headers.get('content-type')||'';if(!contentType.includes('application/json')){const body=(await res.text()).slice(0,500);throw new Error('Flask returned a non-JSON response (HTTP '+res.status+'). Check the Flask terminal. '+body)}const data=await res.json();
if(!data.success){status.className='status bad';status.innerHTML='<h3>'+esc(data.title)+'</h3><p>'+esc(data.message)+'</p>';badge.textContent='ERROR';errors.style.display='block';errors.innerHTML=data.errors.map(x=>'<div class="err"><b>'+esc(x.kind)+' · '+esc(x.code)+' · Line '+esc(String(x.line??'?'))+'</b><br>'+esc(x.message)+'</div>').join('');return}
status.className='status good';status.innerHTML='<h3>✓ DFA is valid</h3><p>Lexical, syntax and semantic checks passed. '+data.dfa.states.length+' states · '+data.dfa.alphabet.length+' symbols · '+data.dfa.transitions.length+' transitions.</p>';badge.textContent='SUCCESS';drawDFA(data.dfa);
}catch(e){status.className='status bad';status.innerHTML='<h3>Application error</h3><p>'+esc(e.message)+'</p>';badge.textContent='FAILED'}}
// Escape compiler messages before placing them in the page.
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
// Arrange the states around a circle and draw the transition arrows.
function drawDFA(d){const svg=document.getElementById('diagram'),W=760,H=430,n=d.states.length,cx=380,cy=220,rx=Math.min(270,90+n*23),ry=Math.min(135,45+n*12);const pos={};d.states.forEach((s,i)=>{let a=-Math.PI/2+2*Math.PI*i/n;pos[s]={x:cx+rx*Math.cos(a),y:cy+ry*Math.sin(a)}});let out='';
out+='<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#c94b45"/></marker></defs>';
// start arrow
let p=pos[d.start_state];out+=`<path d="M ${p.x-65} ${p.y} L ${p.x-34} ${p.y}" stroke="#d8b65b" stroke-width="2.5" marker-end="url(#arr)"/>`;
d.transitions.forEach(t=>{let a=pos[t[0]],b=pos[t[2]];if(!a||!b)return;if(t[0]===t[2]){out+=`<path d="M ${a.x-12} ${a.y-24} C ${a.x-52} ${a.y-82},${a.x+52} ${a.y-82},${a.x+12} ${a.y-24}" fill="none" stroke="#c94b45" stroke-width="2" marker-end="url(#arr)"/><text x="${a.x}" y="${a.y-76}" fill="#f4efeb" text-anchor="middle" font-size="13">${esc(t[1])}</text>`}else{let dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy),ux=dx/len,uy=dy/len,sx=a.x+ux*25,sy=a.y+uy*25,ex=b.x-ux*28,ey=b.y-uy*28,mx=(sx+ex)/2-uy*17,my=(sy+ey)/2+ux*17;out+=`<path d="M ${sx} ${sy} Q ${mx} ${my} ${ex} ${ey}" fill="none" stroke="#c94b45" stroke-width="2" marker-end="url(#arr)"/><text x="${mx}" y="${my-7}" fill="#f4efeb" text-anchor="middle" font-size="12">${esc(t[1])}</text>`}});
d.states.forEach(s=>{let q=pos[s],final=d.final_states.includes(s);out+=`<circle cx="${q.x}" cy="${q.y}" r="25" fill="#182b43" stroke="${final?'#b7ed78':'#45d6d0'}" stroke-width="2.4"/>`;if(final)out+=`<circle cx="${q.x}" cy="${q.y}" r="19" fill="none" stroke="#d8b65b" stroke-width="1.7"/>`;out+=`<text x="${q.x}" y="${q.y+4}" fill="#f1f6ff" text-anchor="middle" font-size="12">${esc(s)}</text>`});svg.innerHTML=out}
</script></body></html>
"""

# Turn a token back into the text used to find its original source line.
def _lexeme_for(token):
    token_type = str(token.type).replace(" ", "_")
    if token.value is not None:
        return str(token.value)
    punctuation = {
        "EQUAL": "=", "COMMA": ",", "LBRACE": "{", "RBRACE": "}",
        "LPAREN": "(", "RPAREN": ")", "ARROW": "->", "CROSS": "X"
    }
    if token_type in punctuation:
        return punctuation[token_type]
    return None

# The existing lexer does not store line numbers, so locate each token in the source.
def attach_line_numbers(source, tokens):
    cursor = 0
    keyword_spellings = ("delta", "DELTA", "q0", "Q", "Σ", "δ", "F")
    for tok in tokens:
        lexeme = _lexeme_for(tok)
        if lexeme is None and str(tok.type).replace(" ", "_") == "KEYWORDS":
            candidates = [(source.find(word, cursor), word) for word in keyword_spellings]
            candidates = [(pos, word) for pos, word in candidates if pos >= 0]
            if candidates:
                pos, lexeme = min(candidates, key=lambda item: item[0])
            else:
                continue
        elif lexeme is not None:
            pos = source.find(lexeme, cursor)
            if pos < 0:
                pos = source.find(lexeme)
        else:
            continue
        if pos >= 0:
            tok.lineno = source.count("\n", 0, pos) + 1
            cursor = pos + len(lexeme)

# The parser returns a dictionary; the semantic checker expects an object with attributes.
def make_semantic_object(d):
    class SemanticDFA:
        pass
    obj = SemanticDFA()
    obj.name = d["name"]
    obj.states = d["states"]
    obj.alphabet = d["alphabet"]
    obj.start_state = d["start_state"]
    obj.final_states = d["final_states"]
    obj.transitions = [(t["from"], t["symbol"], t["to"]) if isinstance(t, dict)
                       else tuple(t) for t in d["transitions"]]
    obj.to_dict = lambda: {
        "name": obj.name,
        "states": obj.states,
        "alphabet": obj.alphabet,
        "start_state": obj.start_state,
        "final_states": obj.final_states,
        "transitions": [
            {"from": source, "symbol": symbol, "to": destination}
            for source, symbol, destination in obj.transitions
        ],
    }
    return obj

# Find the declaration line for errors that do not belong to one transition row.
def declaration_line(source, key):
    for i,line in enumerate(source.splitlines(),1):
        if re.search(r'^\s*'+re.escape(key)+r'\s*=', line):
            return i
    return 1

# Connect semantic diagnostics to the closest useful line in the submitted program.
def semantic_error_lines(source, dfa, errors):
    # Map analyzer diagnostics back to transition/declaration source lines.
    lines = []
    transitions = dfa.get("transitions", [])
    for err in errors:
        code, msg = err["code"], err["message"]
        line = None
        m = re.search(r'Transition (\d+):', msg)
        if m:
            idx = int(m.group(1))-1
            if 0 <= idx < len(transitions):
                line = transitions[idx].get("line") if isinstance(transitions[idx],dict) else None
        if line is None and code == "SEM010":
            # Point to the later occurrence of the repeated state/symbol pair.
            pair = re.search(r'δ\((.*?),\s*(.*?)\)', msg)
            if pair:
                s, sym = pair.group(1), pair.group(2)
                hits = [t.get("line") for t in transitions if isinstance(t,dict) and t["from"]==s and t["symbol"]==sym]
                line = hits[-1] if hits else None
        if line is None and code in ("SEM001","SEM003"):
            line = declaration_line(source, "Q")
        if line is None and code in ("SEM002","SEM004"):
            line = declaration_line(source, "Σ")
        if line is None and code in ("SEM005","SEM006"):
            line = declaration_line(source, "q0" if code=="SEM005" else "F")
        if line is None:
            line = declaration_line(source, "δ")
        lines.append({"kind":"SEMANTIC ERROR","code":code,"line":line,"message":msg})
    return lines

# Show the compiler workspace in the browser.
@app.get("/")
def home():
    return render_template_string(PAGE)

# Run the existing group components in order and return a JSON result to the page.
@app.post("/compile")
def compile_source():
    try:
        payload = request.get_json(silent=True) or {}
        source = payload.get("source", "")
        if not isinstance(source, str) or not source.strip():
            return jsonify(success=False, title="Syntax error",
                           message="No DFA source was provided.",
                           errors=[{"kind":"SYNTAX ERROR","code":"PAR000","line":1,
                                    "message":"Enter a DFA specification before compiling."}]), 400

        from myTokenizer import Lexer
        from parser import parse
        from semantic_analyzer import analyze_dfa

        raw_tokens, lex_error = Lexer(source).tokenizer()
        if lex_error:
            line = getattr(getattr(lex_error, "posStart", None), "ln", 0) + 1
            return jsonify(success=False, title="Lexical error",
                           message="Lexical analysis failed.",
                           errors=[{"kind":"LEXICAL ERROR","code":"LEX","line":line,
                                    "message":str(lex_error)}])

        attach_line_numbers(source, raw_tokens)
        dfa, parse_errors = parse(raw_tokens)
        if parse_errors:
            errors = [{
                "kind": "SYNTAX ERROR",
                "code": error.code,
                "line": error.line or 1,
                "message": error.message
            } for error in parse_errors]
            return jsonify(success=False, title="Syntax error",
                           message="Syntax analysis failed. Fix the reported source line(s).",
                           errors=errors)

        analyzer_dfa = make_semantic_object(dfa)
        result = analyze_dfa(analyzer_dfa)
        if not result["success"]:
            errors = semantic_error_lines(source, dfa, result["errors"])
            return jsonify(success=False, title="Semantic error",
                           message="Semantic analysis failed. The DFA description is structurally valid but has meaning/consistency errors.",
                           errors=errors)

        normalized = {
            "name": dfa["name"],
            "states": dfa["states"],
            "alphabet": dfa["alphabet"],
            "start_state": dfa["start_state"],
            "final_states": dfa["final_states"],
            "transitions": [
                [t["from"], t["symbol"], t["to"]] if isinstance(t, dict) else list(t)
                for t in dfa["transitions"]
            ]
        }
        return jsonify(success=True, dfa=normalized)

    except ModuleNotFoundError as exc:
        return jsonify(success=False, title="Setup error",
                       message="A required Python package or project module is missing.",
                       errors=[{"kind":"SETUP ERROR","code":"SETUP","line":1,
                                "message":f"Missing module: {exc.name}. Run: python -m pip install -r requirements.txt"}]), 500
    except Exception as exc:
        app.logger.exception("Compiler request failed")
        return jsonify(success=False, title="Compiler integration error",
                       message="The compiler encountered an internal error. See the Flask terminal for the traceback.",
                       errors=[{"kind":"APPLICATION ERROR","code":"APP500","line":1,
                                "message":f"{type(exc).__name__}: {exc}"}]), 500

# Start the local development server when this file is run directly.
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
