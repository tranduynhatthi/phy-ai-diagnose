const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');

const appRoot = process.env.PHY_APP_ROOT;
assert(appRoot, 'Set PHY_APP_ROOT');
const fixtureDirectory = fs.mkdtempSync(path.join(os.tmpdir(), 'phy-student-public-'));
let server, browser, context, serverLogs = '';

async function freePort() {
  const socket = net.createServer();
  await new Promise(resolve => socket.listen(0, '127.0.0.1', resolve));
  const port = socket.address().port;
  await new Promise(resolve => socket.close(resolve));
  return port;
}

async function run() {
  const port = await freePort();
  const baseURL = `http://127.0.0.1:${port}`;
  server = spawn(process.env.PHY_PYTHON || 'python3', [
    '-m','uvicorn','app.main:app','--host','127.0.0.1','--port',String(port),
  ], {
    cwd: appRoot,
    env: {
      ...process.env,
      ENVIRONMENT:'test',
      DATABASE_URL:`sqlite:///${fixtureDirectory}/student.db`,
      SECRET_KEY:'student-public-browser-secret',
      LLM_ENABLED:'false',
    },
    stdio:['ignore','pipe','pipe'],
  });
  server.stdout.on('data', x => { serverLogs=(serverLogs+x).slice(-12000); });
  server.stderr.on('data', x => { serverLogs=(serverLogs+x).slice(-12000); });

  let healthy=false;
  for(let i=0;i<100;i++){
    try{healthy=(await fetch(baseURL+'/api/health')).ok}catch{}
    if(healthy)break;
    await new Promise(r=>setTimeout(r,100));
  }
  assert(healthy,'server not healthy');

  browser=await chromium.launch({
    headless:true,
    executablePath:process.env.PHY_CHROMIUM || '/usr/bin/chromium',
    args:['--no-sandbox'],
  });
  context=await browser.newContext({baseURL,viewport:{width:390,height:844}});
  await context.route('https://cdn.jsdelivr.net/**', route => route.abort());
  const page=await context.newPage();
  const pageErrors=[];
  page.on('pageerror',e=>pageErrors.push(e.message));
  await page.goto('/');

  assert.equal(await page.locator('.teacher-portal').count(),0);
  assert.equal(await page.locator('#teacherView').count(),0);
  assert.equal(await page.locator('.student-portal').count(),1);
  assert(await page.locator('#studentPrivacyNotice').isVisible());
  assert((await page.locator('#portalTitle').textContent()).includes('Tự học Vật lí 12'));

  await page.locator('#studentRegistration summary').click();
  await page.locator('#regName').fill('Học sinh tự học');
  await page.locator('#regUser').fill('student_selfstudy_browser');
  await page.locator('#regPass').fill('StudentSelfStudy2026');
  assert.equal(await page.locator('#regClass').getAttribute('type'),'hidden');
  await page.getByRole('button',{name:'Tạo tài khoản học sinh',exact:true}).click();
  await page.locator('#studentView').waitFor({state:'visible'});
  assert(await page.locator('#selfStudyGuide').isVisible());
  const legacyClassCard=page.locator('#studentView [data-student-class-panel="hidden"]');
  assert.equal(await legacyClassCard.count(),1,'student class panel must be retained for JS but hidden');
  assert.equal(await legacyClassCard.isVisible(),false,'student class join card must not be visible');
  assert(await page.locator('#studentView').isVisible(),'student dashboard should remain visible');

  const diag=await page.evaluate(async()=>api('/api/practice/start',{
    method:'POST',
    body:JSON.stringify({chapter:'Chương I',scope:'lesson',lesson:'Bài 1',mode:'diagnostic',intensity:'standard'})
  }));
  await page.evaluate(d=>{
    mode='diagnostic';session=d.session;questions=d.questions;qIndex=0;qAnswered=false;
    show('questionView');renderQuestion();
  },diag);
  await page.locator('#qReasoning').waitFor({state:'visible'});
  const reasoningBox=await page.locator('#qReasoning').boundingBox();
  assert(reasoningBox && reasoningBox.height>=150,'reasoning box should be large');

  const token=await page.evaluate(()=>localStorage.getItem('phy_token'));
  const examStart=await context.request.post('/api/exams/start',{
    headers:{Authorization:'Bearer '+token},
    data:{level:'auto'}
  });
  assert.equal(examStart.status(),200,await examStart.text());
  const exam=await examStart.json();
  const examSubmit=await context.request.post('/api/exams/'+exam.session.id+'/submit',{
    headers:{Authorization:'Bearer '+token},
    data:{answers:{},elapsed_seconds:30}
  });
  assert.equal(examSubmit.status(),200,await examSubmit.text());
  const result=await examSubmit.json();
  assert(result.post_exam_diagnosis,'post-exam diagnosis missing');
  assert(Array.isArray(result.post_exam_diagnosis.profiles));
  assert(result.post_exam_diagnosis.weak_chapter,'weak chapter missing after zero-score exam');

  await page.evaluate(async()=>{
    await api('/api/me',{method:'DELETE'});
    logout();
  });
  assert(await page.locator('#authView').isVisible());
  assert.equal(await page.evaluate(()=>localStorage.getItem('phy_token')),null);
  assert.deepEqual(pageErrors,[],'student public UI JavaScript errors');
  console.log('Student-only self-study browser flow: passed');
}

run().catch(err=>{
  console.error(err.stack);
  if(serverLogs)console.error(serverLogs);
  process.exitCode=1;
}).finally(async()=>{
  if(context)await context.close();
  if(browser)await browser.close();
  if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(r=>server.once('exit',r));}
  fs.rmSync(fixtureDirectory,{recursive:true,force:true});
});
