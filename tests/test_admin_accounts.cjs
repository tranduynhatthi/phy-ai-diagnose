// Admin account-list regressions against an isolated SQLite/Uvicorn instance.
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
const fixtureDirectory = fs.mkdtempSync(path.join(os.tmpdir(), 'phy-admin-accounts-'));
const adminPassword = 'AdminAccountRegression123';
const teacherPassword = 'TeacherAccountRegression123';
const studentPassword = 'StudentAccountRegression123';
let server, browser, context, serverLogs = '';
const releases = [];

async function freePort() {
  const socket = net.createServer();
  await new Promise(resolve => socket.listen(0, '127.0.0.1', resolve));
  const port = socket.address().port;
  await new Promise(resolve => socket.close(resolve));
  return port;
}

async function request(method, route, data, token) {
  const response = await context.request.fetch(route, {
    method, data, headers: token ? { Authorization: 'Bearer ' + token } : {},
  });
  assert.equal(response.status(), 200, `${method} ${route}: ${await response.text()}`);
  return response.json();
}

async function login(page, portal, username, password) {
  await page.locator(`#${portal}LoginUser`).fill(username);
  await page.locator(`#${portal}LoginPass`).fill(password);
  await page.locator(`#${portal}LoginPass`).press('Enter');
  await page.locator(portal === 'student' ? '#studentView' : '#adminView').waitFor({ state: 'visible' });
}

async function logout(page) {
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
  await page.locator('#authView').waitFor({ state: 'visible' });
  assert.equal(await page.evaluate(() => localStorage.getItem('phy_token')), null);
}

async function expectListCount(page, count, total = count) {
  await page.waitForFunction(({ count, total }) => {
    const label = document.getElementById('adminCount').textContent;
    return label.includes(`${count}/${total}`);
  }, { count, total }, { timeout: 5000 });
  if (count) assert.equal(await page.locator('#adminUserRows tr').count(), count);
}

async function screenshot(page, filename) {
  if (!process.env.PHY_SCREENSHOT_DIR) return;
  fs.mkdirSync(process.env.PHY_SCREENSHOT_DIR, { recursive: true });
  await page.screenshot({ path: path.join(process.env.PHY_SCREENSHOT_DIR, filename), fullPage: true });
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
      SECRET_KEY: 'admin-account-regression-secret-never-for-production',
      ADMIN_USERNAME: 'accounts_admin', ADMIN_PASSWORD: adminPassword,
      ADMIN_NAME: 'Quản trị thử nghiệm', FORCE_ADMIN_PASSWORD_RESET: 'false',
      TEACHER_USERNAME: 'accounts_teacher', TEACHER_PASSWORD: teacherPassword,
      TEACHER_NAME: 'Giáo viên thử nghiệm',
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
  await context.route('https://cdn.jsdelivr.net/**', route => route.abort());
  const page = await context.newPage();
  const scriptErrors = [];
  page.on('pageerror', error => scriptErrors.push(error.message));
  const dialogs = [];
  const dismissDialog = async dialog => { dialogs.push(dialog.message()); await dialog.dismiss(); };
  page.on('dialog', dismissDialog);
  const firstStudent = await request('POST', '/api/auth/register', {
    username: 'accounts_student_one', password: studentPassword, display_name: 'Học sinh Một',
  });
  await request('POST', '/api/auth/register', {
    username: 'accounts_student_two', password: studentPassword, display_name: 'Học sinh Hai',
  });
  await page.goto('/');
  await login(page, 'teacher', 'accounts_admin', adminPassword);
  await expectListCount(page, 4);
  assert((await page.locator('#adminUserRows').textContent()).includes('accounts_student_one'));
  assert((await page.locator('#adminUserRows').textContent()).includes('accounts_student_two'));
  console.log('Admin sees registered students and seeded teacher/admin: passed');

  // Reproduce the reported "Hiển thị 0/4": filters from an earlier session
  // must not hide every account when the administrator signs in again.
  await page.locator('#adminSearch').fill('không-có-tài-khoản-này');
  await page.locator('#adminRoleFilter').selectOption('teacher');
  await page.locator('#adminActiveFilter').selectOption('locked');
  await expectListCount(page, 0, 4);
  await screenshot(page, 'admin-accounts-filtered-empty.png');
  await logout(page);
  await login(page, 'teacher', 'accounts_admin', adminPassword);
  await expectListCount(page, 4);
  for (const id of ['adminSearch', 'adminRoleFilter', 'adminActiveFilter']) {
    assert.equal(await page.locator('#' + id).inputValue(), '', `New admin session resets ${id}`);
  }
  assert.equal(await page.locator('#adminSearch').getAttribute('type'), 'search');
  assert.equal(await page.locator('#adminSearch').getAttribute('autocomplete'), 'off');
  console.log('Fresh admin session clears retained zero-result filters: passed');

  await page.locator('#adminSearch').fill('không-có-tài-khoản-này');
  await expectListCount(page, 0, 4);
  await page.locator('#adminUserRows [data-action="clear-admin-filters"]').click();
  await expectListCount(page, 4);
  await page.locator('#adminRoleFilter').selectOption('teacher');
  await expectListCount(page, 1, 4);
  assert((await page.locator('#adminUserRows').textContent()).includes('accounts_teacher'));
  await page.locator('#adminClearFilters').click();
  await expectListCount(page, 4);
  await page.locator('#adminSearch').fill('học sinh');
  await expectListCount(page, 2, 4);
  await page.locator('#adminClearFilters').click();
  await expectListCount(page, 4);
  console.log('Empty-list recovery, explicit clear button and normal filters: passed');

  const outageMessage = 'Không tải được danh sách thử nghiệm';
  await page.route('**/api/admin/users', route => route.fulfill({
    status: 503, contentType: 'application/json', body: JSON.stringify({ detail: outageMessage }),
  }));
  await page.getByRole('button', { name: 'Làm mới', exact: true }).click();
  await page.waitForFunction(message => document.getElementById('adminListMessage').textContent.includes(message), outageMessage);
  assert(await page.locator('#adminRetryList').isVisible());
  assert.equal(dialogs.length, 0, 'Account-list failure should appear inline');
  await page.unroute('**/api/admin/users');
  await page.locator('#adminRetryList').click();
  await expectListCount(page, 4);
  assert(await page.locator('#adminRetryList').isHidden());
  console.log('Account-list API failure and inline retry recovery: passed');

  await screenshot(page, 'admin-accounts-desktop.png');
  await page.setViewportSize({ width: 390, height: 844 });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Mobile admin page overflow');
  assert(await page.locator('#adminClearFilters').isVisible());
  await screenshot(page, 'admin-accounts-mobile.png');
  await page.setViewportSize({ width: 1365, height: 1000 });

  // A privileged list started by an earlier session must not render after
  // logout or a later login. Admin password fields must also be cleared.
  await page.locator('#adminCurrentPassword').fill('CurrentPasswordMustBeCleared');
  await page.locator('#adminNewPassword').fill('NewPasswordMustBeCleared');
  await page.locator('#adminNewPassword2').fill('NewPasswordMustBeCleared');
  let releasePrevious, previousReady;
  const previousGate = new Promise(resolve => { releasePrevious = resolve; releases.push(resolve); });
  const previousFetched = new Promise(resolve => { previousReady = resolve; });
  await page.route('**/api/admin/users', async route => {
    const response = await route.fetch();
    previousReady(); await previousGate; await route.fulfill({ response });
  });
  const previousRequest = page.evaluate(() => loadAdminUsers());
  await previousFetched;
  await logout(page);
  for (const id of ['adminCurrentPassword', 'adminNewPassword', 'adminNewPassword2']) {
    assert.equal(await page.locator('#' + id).inputValue(), '', `Logout clears ${id}`);
  }
  assert.deepEqual(await page.evaluate(() => ({
    users: adminUsers.length, rows: document.getElementById('adminUserRows').textContent,
    stats: document.getElementById('adminStats').textContent,
    count: document.getElementById('adminCount').textContent,
  })), { users: 0, rows: '', stats: '', count: '' });
  await login(page, 'student', firstStudent.user.username, studentPassword);
  releasePrevious(); await previousRequest;
  assert.deepEqual(await page.evaluate(() => ({
    role: me.role, users: adminUsers.length,
    rows: document.getElementById('adminUserRows').textContent,
  })), { role: 'student', users: 0, rows: '' });
  await page.unroute('**/api/admin/users');
  console.log('Logout clears admin state and rejects previous-session account response: passed');

  assert.deepEqual(scriptErrors, []);
  assert.deepEqual(dialogs, []);
  console.log('Admin account list browser regressions: all passed');
}

run().catch(error => {
  console.error(error);
  console.error(serverLogs);
  process.exitCode = 1;
}).finally(async () => {
  for (const release of releases) release();
  if (browser) await browser.close();
  if (server) server.kill('SIGTERM');
  fs.rmSync(fixtureDirectory, { recursive: true, force: true });
});
