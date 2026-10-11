// Browser regressions against an isolated Uvicorn instance and SQLite database.
// Requires Playwright, Chromium, PHY_APP_ROOT and a Python with app dependencies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');

const appRoot = process.env.PHY_APP_ROOT;
assert(appRoot, 'Set PHY_APP_ROOT to the generated application directory');
const fixtureDirectory = fs.mkdtempSync(path.join(os.tmpdir(), 'phy-role-portals-'));
const teacherPassword = 'BrowserTeacherPassword123';
const studentPassword = 'BrowserStudentPassword123';
const adminPassword = 'BrowserAdminPassword123';
let server, browser, context, serverLogs = '';

async function freePort() {
  const socket = net.createServer();
  await new Promise(resolve => socket.listen(0, '127.0.0.1', resolve));
  const port = socket.address().port;
  await new Promise(resolve => socket.close(resolve));
  return port;
}

async function request(client, method, route, data, token) {
  const response = await client.fetch(route, {
    method, data, headers: token ? { Authorization: 'Bearer ' + token } : {},
  });
  assert.equal(response.status(), 200, `${method} ${route}: ${await response.text()}`);
  return response.json();
}

async function login(page, portal, username, password) {
  await page.locator(`#${portal}LoginUser`).fill(username);
  await page.locator(`#${portal}LoginPass`).fill(password);
  await page.locator(`#${portal}LoginPass`).press('Enter');
}

async function logout(page) {
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
  await page.locator('#authView').waitFor({ state: 'visible' });
  assert.equal(await page.evaluate(() => localStorage.getItem('phy_token')), null);
  for (const field of ['teacherLoginPass', 'studentLoginPass', 'regPass']) {
    assert.equal(await page.locator('#' + field).inputValue(), '');
  }
}

async function screenshot(page, name) {
  if (!process.env.PHY_SCREENSHOT_DIR) return;
  fs.mkdirSync(process.env.PHY_SCREENSHOT_DIR, { recursive: true });
  await page.screenshot({ path: path.join(process.env.PHY_SCREENSHOT_DIR, name), fullPage: true });
}

async function run() {
  const port = await freePort();
  const baseURL = `http://127.0.0.1:${port}`;
  server = spawn(process.env.PHY_PYTHON || 'python3', [
    '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(port),
  ], {
    cwd: appRoot,
    env: {
      ...process.env,
      ENVIRONMENT: 'test', DATABASE_URL: `sqlite:///${fixtureDirectory}/browser.db`,
      SECRET_KEY: 'browser-regression-secret-never-for-production',
      TEACHER_USERNAME: 'browser_teacher', TEACHER_PASSWORD: teacherPassword,
      TEACHER_NAME: 'Giáo viên thử nghiệm',
      ADMIN_USERNAME: 'browser_admin', ADMIN_PASSWORD: adminPassword,
      ADMIN_NAME: 'Quản trị thử nghiệm', FORCE_ADMIN_PASSWORD_RESET: 'false',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  server.stdout.on('data', chunk => { serverLogs = (serverLogs + chunk).slice(-12000); });
  server.stderr.on('data', chunk => { serverLogs = (serverLogs + chunk).slice(-12000); });
  server.on('error', error => { serverLogs += error.message; });
  let healthy = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (server.exitCode !== null) throw new Error('Test server stopped during startup');
    try { healthy = (await fetch(baseURL + '/api/health')).ok; } catch {}
    if (healthy) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert(healthy, 'Test server did not become healthy');
  browser = await chromium.launch({
    headless: true, executablePath: process.env.PHY_CHROMIUM || '/usr/bin/chromium',
    args: ['--no-sandbox'],
  });
  context = await browser.newContext({ baseURL, viewport: { width: 1365, height: 1000 } });
  // The tested login/class flows do not use the optional MathJax CDN.
  await context.route('https://cdn.jsdelivr.net/**', route => route.abort());
  const page = await context.newPage();
  const scriptErrors = [];
  page.on('pageerror', error => scriptErrors.push(error.message));
  await page.route('**/api/meta', route => route.fulfill({
    status: 503, contentType: 'application/json', body: '{"detail":"Temporary test outage"}',
  }));
  await page.goto('/');
  await page.waitForFunction(() => ['teacherLoginMsg', 'studentLoginMsg'].every(id =>
    document.getElementById(id).textContent.includes('Không kết nối được máy chủ')));
  await page.unroute('**/api/meta');
  await login(page, 'teacher', 'browser_teacher', teacherPassword);
  await page.locator('#teacherView').waitFor({ state: 'visible' });
  await logout(page);
  console.log('Metadata outage feedback and login recovery: passed');
  await page.evaluate(() => localStorage.setItem('phy_token', 'expired-test-token'));
  await page.reload();
  await page.waitForFunction(() => localStorage.getItem('phy_token') === null);
  assert(await page.locator('#authView').isVisible(), 'Expired login must return to the visible portals');
  await page.evaluate(() => show('removed-view'));
  assert(await page.locator('#authView').isVisible(), 'Unknown destination must keep a visible login');
  await page.locator('#teacherLoginForm').waitFor({ state: 'visible' });
  await page.locator('#studentLoginForm').waitFor({ state: 'visible' });
  assert.equal(await page.locator('.portal-card').count(), 2);
  const desktopCards = await page.locator('.portal-card').evaluateAll(cards => cards.map(card => {
    const box = card.getBoundingClientRect(); return { x: box.x, y: box.y };
  }));
  assert(Math.abs(desktopCards[0].y - desktopCards[1].y) < 2, 'Desktop cards should share a row');
  assert(desktopCards[1].x > desktopCards[0].x);
  await screenshot(page, 'home-desktop.png');
  await page.setViewportSize({ width: 390, height: 844 });
  const mobileCards = await page.locator('.portal-card').evaluateAll(cards => cards.map(card => {
    const box = card.getBoundingClientRect(); return { x: box.x, y: box.y, bottom: box.bottom };
  }));
  assert(mobileCards[1].y >= mobileCards[0].bottom, 'Mobile cards should stack');
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Mobile page overflow');
  await screenshot(page, 'home-mobile.png');
  await page.setViewportSize({ width: 1365, height: 1000 });

  await login(page, 'student', 'browser_teacher', teacherPassword);
  await page.waitForFunction(() => document.getElementById('studentLoginMsg').textContent.toLowerCase().includes('giáo viên'));
  assert.equal(await page.locator('#teacherLoginMsg').textContent(), '');
  assert.equal(await page.evaluate(() => localStorage.getItem('phy_token')), null);
  assert(await page.locator('#authView').isVisible());
  console.log('Separate portals, responsive layout and wrong-portal rejection: passed');

  await login(page, 'teacher', 'browser_teacher', 'incorrect_password');
  await page.waitForFunction(() => document.getElementById('teacherLoginMsg').textContent.includes('không đúng'));
  await login(page, 'teacher', 'browser_teacher', teacherPassword);
  await page.locator('#teacherView').waitFor({ state: 'visible' });
  await page.waitForFunction(() => document.getElementById('classList').textContent.includes('Bạn chưa có lớp'));
  assert(await page.locator('#schoolSelect').isVisible(), 'Teacher school workspace must remain available');
  page.once('dialog', dialog => dialog.accept('Trường thử nghiệm'));
  await page.getByRole('button', { name: 'Tạo trường', exact: true }).click();
  await page.waitForFunction(() => document.getElementById('schoolIdentity').textContent.includes('Trường thử nghiệm'));
  page.once('dialog', dialog => dialog.accept('12A1 của tôi'));
  await page.getByRole('button', { name: 'Tạo lớp', exact: true }).click();
  await page.waitForFunction(() => document.getElementById('classList').textContent.includes('12A1 của tôi'));
  const teacherToken = await page.evaluate(() => localStorage.getItem('phy_token'));
  const classes = await request(context.request, 'GET', '/api/classes', undefined, teacherToken);
  assert.equal(classes.length, 1);
  const ownClass = classes[0];
  await logout(page);

  await page.locator('#studentRegistration summary').click();
  await page.locator('#regName').fill('Học sinh lớp 12A1');
  await page.locator('#regUser').fill('browser_student');
  await page.locator('#regPass').fill(studentPassword);
  await page.locator('#regClass').fill(ownClass.join_code.toLowerCase());
  await page.getByRole('button', { name: 'Tạo tài khoản học sinh', exact: true }).click();
  await page.locator('#studentView').waitFor({ state: 'visible' });
  assert((await page.locator('#studentClasses').textContent()).includes(ownClass.name));
  await page.waitForFunction(() => document.getElementById('studentSchoolLine').textContent.includes('Trường thử nghiệm'));
  assert((await page.locator('#studentWelcome').textContent()).includes('Học sinh lớp 12A1'));
  assert.equal(await page.locator('#studentHomeStats .home-stat').count(), 4);
  const studentToken = await page.evaluate(() => localStorage.getItem('phy_token'));
  const student = (await request(context.request, 'GET', '/api/me', undefined, studentToken)).user;
  await logout(page);
  await login(page, 'teacher', 'browser_student', studentPassword);
  await page.waitForFunction(() => document.getElementById('teacherLoginMsg').textContent.toLowerCase().includes('học sinh'));
  assert.equal(await page.evaluate(() => localStorage.getItem('phy_token')), null);
  await login(page, 'student', 'browser_student', studentPassword);
  await page.locator('#studentView').waitFor({ state: 'visible' });
  await logout(page);
  console.log('Student registration, class enrollment and student login: passed');

  await login(page, 'teacher', 'browser_teacher', teacherPassword);
  await page.locator('#teacherView').waitFor({ state: 'visible' });
  await page.waitForFunction(() => document.getElementById('studentProgressRows').textContent.includes('browser_student'));
  await page.waitForFunction(() => document.getElementById('schoolStudentRows').textContent.includes('browser_student'));
  assert((await page.locator('#schoolClassRows').textContent()).includes(ownClass.name));
  console.log('School workspace and personal student dashboard preserved: passed');
  await page.locator('#studentProgressRows').getByRole('button', { name: 'Xem', exact: true }).click();
  await page.locator('#studentDetailCard').waitFor({ state: 'visible' });
  assert((await page.locator('#studentDetailTitle').textContent()).includes(student.display_name));
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Tải báo cáo CSV', exact: true }).click();
  const download = await downloadPromise;
  const csv = fs.readFileSync(await download.path(), 'utf8');
  assert(csv.includes(student.username));
  assert.equal(download.suggestedFilename(), 'phy_ai_student_report.csv');
  const resetResponse = page.waitForResponse(response => response.url().includes('/reset-password') && response.request().method() === 'POST');
  let dialogStep = 0;
  let completeReset;
  const resetFinished = new Promise(resolve => { completeReset = resolve; });
  const acceptReset = async dialog => {
    if (dialogStep++ === 0) await dialog.accept('ResetStudentPassword123');
    else {
      await dialog.accept();
      if (dialogStep === 3) completeReset();
    }
  };
  page.on('dialog', acceptReset);
  await page.getByRole('button', { name: 'Đặt lại mật khẩu', exact: true }).click();
  assert.equal((await resetResponse).status(), 200);
  await resetFinished;
  page.off('dialog', acceptReset);
  const changed = await request(context.request, 'POST', '/api/auth/login', {
    username: student.username, password: 'ResetStudentPassword123', portal: 'student',
  });
  assert.equal(changed.user.id, student.id);
  await screenshot(page, 'teacher-class.png');

  // A late response must not overwrite a newer class or pupil selection.
  const secondStudent = await request(context.request, 'POST', '/api/auth/register', {
    username: 'browser_second_student', password: studentPassword,
    display_name: 'Học sinh thứ hai', class_code: ownClass.join_code,
  });
  const secondClass = await request(context.request, 'POST', '/api/classes', {
    name: '12A2 của tôi',
  }, await page.evaluate(() => localStorage.getItem('phy_token')));
  let releaseClass, classReady;
  const classGate = new Promise(resolve => { releaseClass = resolve; });
  const classFetched = new Promise(resolve => { classReady = resolve; });
  const classPattern = `**/api/teacher/v2/classes/${ownClass.id}/dashboard*`;
  await page.route(classPattern, async route => {
    const response = await route.fetch();
    classReady(); await classGate; await route.fulfill({ response });
  });
  const oldClassRequest = page.evaluate(id => selectClass(id), ownClass.id);
  await classFetched;
  await page.evaluate(id => selectClass(id), secondClass.id);
  releaseClass(); await oldClassRequest;
  assert((await page.locator('#classHint').textContent()).includes(secondClass.name));
  assert(!(await page.locator('#studentProgressRows').textContent()).includes(student.username));
  await page.unroute(classPattern);
  await page.evaluate(id => selectClass(id), ownClass.id);
  let releaseStudent, studentReady;
  const studentGate = new Promise(resolve => { releaseStudent = resolve; });
  const studentFetched = new Promise(resolve => { studentReady = resolve; });
  const studentPattern = `**/api/teacher/v2/students/${student.id}/progress*`;
  await page.route(studentPattern, async route => {
    const response = await route.fetch();
    studentReady(); await studentGate; await route.fulfill({ response });
  });
  const oldStudentRequest = page.evaluate(id => viewStudentProgress(id), student.id);
  await studentFetched;
  await page.evaluate(id => viewStudentProgress(id), secondStudent.user.id);
  releaseStudent(); await oldStudentRequest;
  assert((await page.locator('#studentDetailTitle').textContent()).includes(secondStudent.user.display_name));
  assert.equal(await page.evaluate(() => currentStudentId), secondStudent.user.id);
  await page.unroute(studentPattern);
  console.log('Late class and pupil responses preserve the current selection: passed');
  await logout(page);
  console.log('Teacher roster, individual report and student password management: passed');

  await login(page, 'teacher', 'browser_admin', adminPassword);
  await page.locator('#adminView').waitFor({ state: 'visible' });
  assert(await page.locator('#teacherView').isHidden());
  const adminToken = await page.evaluate(() => localStorage.getItem('phy_token'));
  const other = await request(context.request, 'POST', '/api/auth/register', {
    username: 'browser_other_teacher', password: teacherPassword, display_name: 'Giáo viên lớp khác',
  });
  await request(context.request, 'POST', '/api/admin/promote', { user_id: other.user.id, role: 'teacher' }, adminToken);
  const otherLogin = await request(context.request, 'POST', '/api/auth/login', {
    username: 'browser_other_teacher', password: teacherPassword, portal: 'teacher',
  });
  await request(context.request, 'POST', '/api/classes', { name: '12B2 lớp khác' }, otherLogin.token);
  await logout(page);

  await login(page, 'teacher', 'browser_teacher', teacherPassword);
  await page.locator('#teacherView').waitFor({ state: 'visible' });
  await page.evaluate(id => selectClass(id), ownClass.id);
  let releaseOldSession, oldSessionReady;
  const oldSessionGate = new Promise(resolve => { releaseOldSession = resolve; });
  const oldSessionFetched = new Promise(resolve => { oldSessionReady = resolve; });
  await page.route(studentPattern, async route => {
    const response = await route.fetch();
    oldSessionReady(); await oldSessionGate; await route.fulfill({ response });
  });
  const previousTeacherRequest = page.evaluate(id => viewStudentProgress(id), student.id);
  await oldSessionFetched;
  const schoolId = await page.evaluate(() => currentSchoolId);
  let releaseOldSchool, oldSchoolReady;
  const oldSchoolGate = new Promise(resolve => { releaseOldSchool = resolve; });
  const oldSchoolFetched = new Promise(resolve => { oldSchoolReady = resolve; });
  const schoolPattern = `**/api/teacher/schools/${schoolId}/dashboard`;
  await page.route(schoolPattern, async route => {
    const response = await route.fetch();
    oldSchoolReady(); await oldSchoolGate; await route.fulfill({ response });
  });
  const previousSchoolRequest = page.evaluate(id => selectSchool(id), schoolId);
  await oldSchoolFetched;
  await logout(page);
  await login(page, 'teacher', 'browser_other_teacher', teacherPassword);
  await page.waitForFunction(() => document.getElementById('classList').textContent.includes('12B2 lớp khác'));
  releaseOldSession(); await previousTeacherRequest;
  releaseOldSchool(); await previousSchoolRequest;
  assert(!(await page.locator('#classList').textContent()).includes('12A1 của tôi'));
  assert(!(await page.locator('#studentProgressRows').textContent()).includes('browser_student'));
  assert(await page.locator('#studentDetailCard').isHidden());
  assert(!(await page.locator('#schoolIdentity').textContent()).includes('Trường thử nghiệm'));
  assert(await page.locator('#schoolDetailCard').isHidden());
  assert.deepEqual(scriptErrors, [], 'Browser JavaScript errors');
  console.log('Admin login and isolation after changing teacher accounts: passed');
}

run().catch(error => {
  console.error(error.stack);
  if (serverLogs) console.error(serverLogs);
  process.exitCode = 1;
}).finally(async () => {
  if (context) await context.close();
  if (browser) await browser.close();
  if (server && server.exitCode === null) {
    server.kill('SIGTERM');
    await new Promise(resolve => server.once('exit', resolve));
  }
  fs.rmSync(fixtureDirectory, { recursive: true, force: true });
});
