// Renderer regressions against the assembled production frontend and real MathJax.
// PHY_APP_ROOT points to the application assembled by the Docker patch sequence.
// PHY_BANK_JSON (or PHY_BANK_FIXTURE) is the effective exported question bank; PHY_MATHJAX_ROOT is a
// mathjax-full@3.2.2 installation (npm install it outside the repository).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const vm = require('node:vm');
const { chromium } = require('playwright');

const auditDir = process.env.PHY_MATH_AUDIT_DIR || '/workspace/phy-ai-diagnose-runtime/question-audit';
const appRoot = process.env.PHY_APP_ROOT;
assert(appRoot, 'Set PHY_APP_ROOT to the generated application directory');
const bankPath = process.env.PHY_BANK_JSON || process.env.PHY_BANK_FIXTURE || path.join(auditDir, 'bank-current.json');
let mathRoot = process.env.PHY_MATHJAX_ROOT;
if (!mathRoot) {
  try { mathRoot = path.dirname(require.resolve('mathjax-full/package.json')); }
  catch { mathRoot = path.join(auditDir, 'math-tools/node_modules/mathjax-full'); }
}
const frontend = fs.readFileSync(path.join(appRoot, 'app/static/index.html'), 'utf8');
assert.equal((frontend.match(/PHY_AI_LATEX_UNIFIED_V3/g) || []).length, 1);
assert(frontend.includes('mathjax@3.2.2/es5/tex-chtml.js'), 'Production MathJax must match the tested version');
const helper = frontend.slice(frontend.indexOf('function texCore('), frontend.indexOf('async function api('));
const sandbox = { window: {}, console };
vm.createContext(sandbox);
vm.runInContext(helper + '\nthis.mathHtml=mathHtml;this.segments=phyMath.segments;', sandbox);
const html = sandbox.mathHtml;
const fixtures = [
  ['120 J', String.raw`\(120\,\mathrm{J}\)`],
  ['-120 J', String.raw`\(-120\,\mathrm{J}\)`],
  ['225 J', String.raw`\(225\,\mathrm{J}\)`],
  ['180 J', String.raw`\(180\,\mathrm{J}\)`],
  ['A = 150 J', String.raw`\(A = 150\,\mathrm{J}\)`],
  ['B = 0.4 T', String.raw`\(B = 0.4\,\mathrm{T}\)`],
  ['150J', String.raw`\(150\,\mathrm{J}\)`],
  ['16U1', String.raw`\(16 U_{1}\)`],
  ['J/(kg.K)', String.raw`\(\frac{\mathrm{J}}{\mathrm{kg}\,\mathrm{K}}\)`],
  ['m/s²', String.raw`\(\frac{\mathrm{m}}{\mathrm{s}^{2}}\)`],
  ['2 μA', String.raw`\(2\,\mathrm{\mu A}\)`],
  ['37 °C', String.raw`\(37\,{}^{\circ}\mathrm{C}\)`],
  ['1/2', String.raw`\(\frac{1}{2}\)`],
  ['U-235', String.raw`\({}^{235}\mathrm{U}\)`],
  ['235U', String.raw`\({}^{235}\mathrm{U}\)`],
  ['14C', String.raw`\(14\,\mathrm{C}\)`],
  ['p₁ = 2 atm', String.raw`\(p_{1} = 2\,\mathrm{atm}\)`],
  ['Q_hữu ích = 40 J', String.raw`\(Q_{\text{hữu ích}} = 40\,\mathrm{J}\)`],
  [String.raw`\(\frac{1}{2}mv^2 + \mathrm{J}\)`, String.raw`\(\frac{1}{2}mv^2 + \mathrm{J}\)`],
  [String.raw`\[p_1V_1 = p_2V_2\]`, String.raw`\[p_1V_1 = p_2V_2\]`],
  ['$p_1 = 2$', String.raw`\(p_1 = 2\)`],
  [String.raw`$$\alpha + \beta$$`, String.raw`\[\alpha + \beta\]`],
  ['Sau biến đổi, áp suất tăng. Trong vật rắn, các hạt dao động.', 'Sau biến đổi, áp suất tăng. Trong vật rắn, các hạt dao động.'],
  ['@@M0@@ @@U0@@', '@@M0@@ @@U0@@'],
  ['Ē = 3kT/2', String.raw`\(\overline{E} = 3 \frac{kT}{2}\)`],
  ['sin30° = 1/2', String.raw`\(\sin  30\,{}^{\circ} = \frac{1}{2}\)`],
  ['e=E0cos(ωt+φ)', String.raw`\(e = E_{0} \cos  (\omega t + \varphi )\)`],
  ['|Φ| = BS', String.raw`\(\lvert \Phi \rvert  = BS\)`],
  ['F = BIl sinα', String.raw`\(F = BIl \sin  \alpha \)`],
  ['1.6 x 10^-19 C', String.raw`\(1.6 \times  10^{-19}\,\mathrm{C}\)`],
  [String.raw`\({}^{235}_{92}\mathrm{U} \to {}^{231}_{90}\mathrm{Th} + {}^{4}_{2}\mathrm{He}\)`, String.raw`\({}^{235}_{92}\mathrm{U} \to {}^{231}_{90}\mathrm{Th} + {}^{4}_{2}\mathrm{He}\)`],
  ['T(K)≈t(°C)+273', String.raw`\(T (\mathrm{K}) \approx  t ({}^{\circ}\mathrm{C}) + 273\)`],
  ['ρ=1 kg/L', String.raw`\(\rho  = 1\,\frac{\mathrm{kg}}{\mathrm{L}}\)`],
  [String.raw`\alpha_1 + \frac{1}{2}mv^2`, String.raw`\(\alpha_{1} + \frac{1}{2} mv^{2}\)`],
  ['3,34444…×10^22', String.raw`\(3{,}34444\ldots  \times  10^{22}\)`],
  ['2,666… L', String.raw`\(2{,}666\ldots \,\mathrm{L}\)`],
  ['3T', String.raw`\(3 T\)`],
  ['Sau 2T, số hạt nhân mẹ giảm.', String.raw`Sau \(2 T\), số hạt nhân mẹ giảm.`],
  ['Sau 3T, hoạt độ giảm.', String.raw`Sau \(3 T\), hoạt độ giảm.`],
  ['B=0.4T', String.raw`\(B = 0.4\,\mathrm{T}\)`],
  ['6h', String.raw`\(6\,\mathrm{h}\)`],
  ['10 min', String.raw`\(10\,\mathrm{min}\)`],
  ['E = hν', String.raw`\(E = h\nu \)`],
  ['T2=T1p2/p1', String.raw`\(T_{2} = \frac{T_{1}p_{2}}{p_{1}}\)`],
  ['E hạt nhân = E phân hạch×N', String.raw`\(E_{\text{hạt nhân}} = E_{\text{phân hạch}} \times  N\)`],
  ['1/18 mol', String.raw`\(\frac{1}{18}\,\mathrm{mol}\)`],
  ['80/(1/2)^3', String.raw`\(\frac{80}{(\frac{1}{2})^{3}}\)`],
  ['-(1/2)/3', String.raw`\(\frac{-\frac{1}{2}}{3}\)`],
  ['V2', String.raw`\(V_{2}\)`],
  ['W riêng=W/A', String.raw`\(W_{\text{riêng}} = \frac{W}{A}\)`],
];
for (const [input, expected] of fixtures) assert.equal(html(input), expected, input);
assert.match(html('1,8×10^5 J/kg'), /1\{,\}8.*\\times.*10\^\{5\}.*\\mathrm\{J\}.*\\mathrm\{kg\}/);
assert.match(html('6.02e23 mol^-1'), /6\.02\\times 10\^\{23\}.*\\mathrm\{mol\}\^\{-1\}/);
assert.match(html('p2=p1V1T2/(T1V2)=2.4 atm.'), /p_\{2\} = \\frac\{p_\{1\}V_\{1\}T_\{2\}\}\{T_\{1\}V_\{2\}\} = 2\.4/);
const bank = JSON.parse(fs.readFileSync(bankPath, 'utf8'));
assert.equal(bank.questions.length, 1000, 'Audit must cover the complete 1,000-question bank');
const values = [];
function add(value, key) {
  if (typeof value === 'string') values.push({ key, raw: value });
  else if (Array.isArray(value)) value.forEach((v, i) => add(v, key + '.' + i));
  else if (value && typeof value === 'object') for (const [k, v] of Object.entries(value)) {
    if (['prompt', 'q', 'options', 'statements', 'text', 'explain', 'unit', 'concept', 'contrast', 'tip', 'guided', 'transfer'].includes(k)) add(v, key + '.' + k);
  }
}
for (const question of bank.questions) add(question, question.id);
for (const error of bank.errors) add(error.repair, 'repair.' + error.id);
let formulaCount = 0;
const asciiEqualityText = [];
for (const field of values) {
  const generated = html(field.raw, field.key.endsWith('.unit') ? 'unit' : undefined);
  assert(!/@@[MU]\d+@@/.test(generated), field.key + ': leaked sentinel');
  for (const segment of sandbox.segments(field.raw, field.key.endsWith('.unit') ? 'unit' : undefined)) {
    if (segment.kind === 'text') {
      if (segment.text.includes('=')) {
        // Descriptive prose labels can precede an equals sign. A variable or
        // arithmetic expression remaining beside it means extraction failed.
        assert(!/=\s*[A-Za-z0-9]|(?:[A-Za-z]\d+|\b[A-Z])\s*=|[*/]/u.test(segment.text), field.key + ': unconverted ASCII equation: ' + segment.text);
        asciiEqualityText.push({ key: field.key, text: segment.text, assessment: 'descriptive prose label; mathematical operand rendered separately' });
      }
      assert(!/[ΔΦφλρηωαβγθμπσετΩν√_^⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉×·]|Ē|(?:sin|cos|tan|ln)\d/u.test(segment.text), field.key + ': unconverted formula: ' + segment.text);
      continue;
    }
    formulaCount++;
    assert(!/\\[()[\]]|\$/.test(segment.tex), field.key + ': nested math delimiter');
    assert(!/[À-ỹ]/u.test(segment.tex.replace(/\\text\{[^}]*\}/g, '')), field.key + ': prose inside math: ' + segment.tex);
  }
}
const screenshotQuestion = bank.questions.find(q => q.id === 'EXT-02-M05');
assert.deepEqual(screenshotQuestion.options, ['120 J', '-120 J', '225 J', '180 J']);
const gasQuestion = bank.questions.find(q => q.id === 'NEW-13-VDC-M02');
for (const part of ['p_{1} = 1.2', 'V_{1} = 4.0', 'T_{1} = 300', 'V_{2} = 3.0', 'T_{2} = 450']) assert(html(gasQuestion.prompt).includes(part), part);

let browser, server;
const pageErrors = [];
const report = { bankPath, bankVersion: bank.version, asciiEqualityTextSegments: asciiEqualityText.length, questions: bank.questions.length, fields: values.length, mathSegments: formulaCount, fixtures: fixtures.length + 3, typesetFields: 0, typesetExpressions: 0, renderPaths: [], errors: [] };
async function run() {
  fs.mkdirSync(auditDir, { recursive: true });
  fs.writeFileSync(path.join(auditDir, 'math-ascii-equation-audit.json'), JSON.stringify({ bankPath, bankVersion: bank.version, unconvertedEquations: 0, residualProseLabels: asciiEqualityText }, null, 2) + '\n');
  server = http.createServer((req, res) => {
    if (req.url === '/') { res.setHeader('Content-Type', 'text/html'); res.end(frontend); return; }
    if (req.url === '/api/meta') { res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify({ chapters: bank.chapters, lessonNames: bank.lessonNames })); return; }
    res.statusCode = 404; res.end();
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  browser = await chromium.launch({ executablePath: process.env.PHY_CHROMIUM || '/usr/bin/chromium', headless: true, args: ['--no-sandbox'] });
  const context = await browser.newContext({ viewport: { width: 1365, height: 1000 } });
  await context.route(/^https:\/\/cdn\.jsdelivr\.net\/npm\/mathjax@3(?:\.2\.2)?\//, async route => {
    const resource = route.request().url().replace(/^https:\/\/cdn\.jsdelivr\.net\/npm\/mathjax@3(?:\.2\.2)?\//, '');
    const local = path.resolve(mathRoot, resource);
    assert(local.startsWith(path.resolve(mathRoot) + path.sep));
    await route.fulfill({ path: local, contentType: local.endsWith('.js') ? 'text/javascript' : 'application/octet-stream' });
  });
  const page = await context.newPage();
  page.on('pageerror', e => pageErrors.push(e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  await page.waitForFunction(() => window.MathJax && MathJax.typesetPromise);
  await page.evaluate(() => MathJax.startup.promise);
  const chunks = [...values, ...fixtures.map(([raw], i) => ({ raw, key: 'fixture.' + i }))];
  for (let start = 0; start < chunks.length; start += 200) {
    const result = await page.evaluate(async fields => {
      let container = document.getElementById('math-bank-audit');
      if (!container) { container = document.createElement('section'); container.id = 'math-bank-audit'; container.style.position = 'absolute'; container.style.left = '-20000px'; document.body.append(container); }
      MathJax.typesetClear([container]);
      container.innerHTML = fields.map(f => '<div data-field="' + esc(f.key) + '">' + mathHtml(f.raw, f.key.endsWith('.unit') ? 'unit' : undefined) + '</div>').join('');
      await typesetMath(container);
      const errors = [...container.querySelectorAll('mjx-merror,[data-mjx-error]')].map(el => ({ key: el.closest('[data-field]').dataset.field, error: el.outerHTML }));
      const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) if (!walker.currentNode.parentElement.closest('mjx-container') && (/\\[()[\]]/.test(walker.currentNode.textContent) || /@@[MU]\d+@@/.test(walker.currentNode.textContent) && !fields.find(f => f.key === walker.currentNode.parentElement.closest('[data-field]').dataset.field).raw.includes('@@'))) errors.push({ key: walker.currentNode.parentElement.closest('[data-field]').dataset.field, error: 'Unrendered math: ' + walker.currentNode.textContent });
      return { errors, count: container.querySelectorAll('mjx-container').length, fields: fields.length };
    }, chunks.slice(start, start + 200));
    report.typesetFields += result.fields; report.typesetExpressions += result.count; report.errors.push(...result.errors);
    if (start % 1000 === 0) console.log(`MathJax fields checked: ${Math.min(start + 200, chunks.length)}/${chunks.length}`);
  }
  assert.deepEqual(report.errors, [], 'Full-bank live MathJax rendering errors');
  await page.evaluate(() => { const el = document.getElementById('math-bank-audit'); MathJax.typesetClear([el]); el.remove(); });
  async function verifyPath(label, selector, minimum = 1) {
    await page.evaluate(() => typesetMath());
    const view = page.locator(selector);
    assert(await view.locator('mjx-container').count() >= minimum, label + ': math was not typeset');
    assert.equal(await view.locator('mjx-merror,[data-mjx-error]').count(), 0, label + ': MathJax error');
    const plain = await view.evaluate(el => { const copy = el.cloneNode(true); copy.querySelectorAll('mjx-container').forEach(n => n.remove()); return copy.textContent; });
    assert(!/\\[()[\]]|@@[MU]\d+@@/.test(plain), label + ': raw delimiters/placeholders');
    report.renderPaths.push(label);
  }
  await page.evaluate(q => { questions = [q]; qIndex = 0; session = { id: 'math-test' }; mode = 'practice'; show('questionView'); renderQuestion(); }, screenshotQuestion);
  await verifyPath('practice prompt and choices', '#questionView', 8);
  await page.screenshot({ path: path.join(auditDir, 'latex-energy-practice.png'), fullPage: true });
  await page.route('**/api/practice/math-test/answer', route => route.fulfill({ json: { correct: true, explain: screenshotQuestion.explain } }));
  await page.locator('input[name="qa"][value="3"]').check();
  await page.evaluate(() => submitCurrentAnswer());
  await verifyPath('practice feedback', '#qFeedback');
  await page.route('**/api/repair/start', route => route.fulfill({ json: { session: { id: 'math-repair' }, error: { id: 'math', title: 'Test', concept: 'ΔU = A + Q.', contrast: 'Q_tỏa = Q_thu.' }, questions: [screenshotQuestion] } }));
  await page.evaluate(() => startRepair('math'));
  await verifyPath('repair concept, contrast, prompt and choices', '#repairView', 10);
  await page.route('**/api/repair/math-repair/answer', route => route.fulfill({ json: { correct: true, explain: screenshotQuestion.explain } }));
  await page.locator('input[name="ra"][value="3"]').check();
  await page.evaluate(() => submitRepair());
  await verifyPath('repair feedback', '#repairFeedback');
  const tf = bank.questions.find(q => q.type === 'tf' && /[=^_Δ]/.test(q.statements.map(s => s.text).join(' ')));
  await page.evaluate(q => { questions = [q]; qIndex = 0; show('questionView'); renderQuestion(); }, tf);
  await verifyPath('true/false statements', '#qAnswer');
  const short = bank.questions.find(q => q.type === 'short' && q.unit === '°C') || bank.questions.find(q => q.unit === '°C');
  await page.evaluate(q => { questions = [q]; qIndex = 0; renderQuestion(); }, short);
  await verifyPath('short-answer unit', '#qAnswer');
  await page.evaluate(q => { examQuestions = [q]; examIndex = 0; exam = { session: { id: 'math-exam' } }; examAnswers = {}; examStarted = Date.now(); show('examView'); renderExamQuestion(); }, gasQuestion);
  await verifyPath('exam prompt and choices', '#examView', 8);
  await page.screenshot({ path: path.join(auditDir, 'latex-gas-exam.png'), fullPage: true });
  await page.route('**/api/exams/math-exam/submit', route => route.fulfill({ json: { result: { total: 10, part1: 10, part2: 0, part3: 0 }, review: [{ question: gasQuestion, correct_answer: 2.4, unit: 'atm' }] } }));
  await page.evaluate(() => submitExam(true));
  await verifyPath('exam result review', '#examResultView');
  await page.evaluate(() => { window.mathXss = 0; const el = document.createElement('div'); el.id = 'math-xss'; el.innerHTML = mathHtml('<img src=x onerror="window.mathXss=1"><script>window.mathXss=1</script>') + mathHtml(String.raw`\(<img src=x onerror="window.mathXss=1">\)`); document.body.append(el); });
  assert.equal(await page.locator('#math-xss img,#math-xss script').count(), 0);
  assert.equal(await page.evaluate(() => window.mathXss), 0);
  assert.deepEqual(pageErrors, [], 'Frontend script errors');
  report.status = 'passed';
  fs.writeFileSync(path.join(auditDir, 'math-rendering-report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
}
run().catch(error => { report.status = 'failed'; report.failure = error.stack; fs.mkdirSync(auditDir, { recursive: true }); fs.writeFileSync(path.join(auditDir, 'math-rendering-report.json'), JSON.stringify(report, null, 2) + '\n'); console.error(error.stack); process.exitCode = 1; }).finally(async () => { if (browser) await browser.close(); if (server) await new Promise(resolve => server.close(resolve)); });
