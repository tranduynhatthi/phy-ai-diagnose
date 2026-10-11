"""Keep registered accounts visible when entering the administrator workspace."""

from pathlib import Path
import re
import sys


ADMIN_LIST_JS = r'''
function resetAdminFilters(render=true){
 for(const id of ['adminSearch','adminRoleFilter','adminActiveFilter'])$(id).value='';
 if(render)renderAdminUsers();
}
function clearAdminState(){
 adminRequestVersion++;adminUsers=[];
 resetAdminFilters(false);
 for(const id of ['adminStats','adminUserRows','adminCount','adminListMessage'])$(id).textContent='';
 for(const id of ['adminCurrentPassword','adminNewPassword','adminNewPassword2'])$(id).value='';
 $('adminRetryList').classList.add('hidden');
}
async function loadAdminUsers(resetFilters=false){
 if(!me||me.role!=='admin')return;
 const request=++adminRequestVersion,sessionToken=token;
 if(resetFilters)resetAdminFilters(false);
 adminUsers=[];$('adminStats').textContent='';$('adminCount').textContent='';
 $('adminUserRows').innerHTML='<tr><td colspan="6" class="muted">Đang tải tài khoản đã đăng kí…</td></tr>';
 $('adminListMessage').textContent='Đang tải danh sách…';
 $('adminRetryList').classList.add('hidden');
 try{
  const users=await api('/api/admin/users');
  if(request!==adminRequestVersion||sessionToken!==token||!me||me.role!=='admin')return;
  if(!Array.isArray(users))throw new Error('Dữ liệu danh sách tài khoản không hợp lệ.');
  adminUsers=users;
  const students=users.filter(x=>x.role==='student').length,teachers=users.filter(x=>x.role==='teacher').length,locked=users.filter(x=>!x.is_active).length;
  $('adminStats').innerHTML=`<div class="stat"><b>${users.length}</b><span>tài khoản</span></div><div class="stat"><b>${students}</b><span>học sinh</span></div><div class="stat"><b>${teachers}</b><span>giáo viên</span></div><div class="stat"><b>${locked}</b><span>đã khóa</span></div>`;
  renderAdminUsers();
 }catch(e){
  if(request!==adminRequestVersion||sessionToken!==token||!me||me.role!=='admin')return;
  $('adminUserRows').innerHTML='<tr><td colspan="6" class="muted">Chưa tải được danh sách tài khoản.</td></tr>';
  $('adminListMessage').textContent=e.message;
  $('adminRetryList').classList.remove('hidden');
 }
}
'''


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Admin account patch: expected one marker {old[:80]!r}")
    return source.replace(old, new, 1)


def apply_patch(root=Path("/app")):
    frontend = Path(root) / "app/static/index.html"
    html = frontend.read_text(encoding="utf-8")
    if 'id="adminClearFilters"' in html:
        return
    html = replace_once(
        html,
        '<input id="adminSearch" placeholder="Nhập từ khóa..."',
        '<input id="adminSearch" type="search" name="admin_account_search" autocomplete="off" placeholder="Nhập từ khóa..."',
    )
    html = replace_once(
        html,
        '<span id="adminCount" class="small muted"></span>',
        '<div class="actions"><span id="adminCount" class="small muted"></span><button id="adminClearFilters" type="button" class="btn ghost" onclick="resetAdminFilters()">Xóa bộ lọc</button></div>',
    )
    html = replace_once(
        html,
        '<tbody id="adminUserRows"></tbody>\n  </table></div>',
        '<tbody id="adminUserRows"></tbody>\n  </table></div>\n  <div class="actions" style="margin-top:12px"><span id="adminListMessage" class="small muted" role="status" aria-live="polite"></span><button id="adminRetryList" type="button" class="btn secondary hidden" onclick="loadAdminUsers()">Thử tải lại</button></div>',
    )
    html = replace_once(html, "let adminUsers=[];", "let adminUsers=[],adminRequestVersion=0;")
    html, count = re.subn(
        r"^async function loadAdminUsers\(\)\{.*?^\}\n",
        lambda _: ADMIN_LIST_JS.lstrip(), html, count=1, flags=re.M | re.S,
    )
    if count != 1:
        raise ValueError("Admin account patch: list loader marker missing")
    html = replace_once(
        html,
        "show('adminView');loadAdminUsers()",
        "show('adminView');loadAdminUsers(true)",
    )
    html = replace_once(
        html,
        "localStorage.removeItem('phy_token');clearAuthForms();show('authView');renderTop();",
        "localStorage.removeItem('phy_token');clearAuthForms();clearAdminState();show('authView');renderTop();",
    )
    html = replace_once(
        html,
        "$('adminCount').textContent=`Hiển thị ${rows.length}/${adminUsers.length}`;",
        "$('adminCount').textContent=`Hiển thị ${rows.length}/${adminUsers.length}`;\n $('adminListMessage').textContent=rows.length?`Đã tải ${adminUsers.length} tài khoản. Khi cần xem tất cả, chọn Xóa bộ lọc.`:adminUsers.length?`Đã tải ${adminUsers.length} tài khoản, nhưng không có tài khoản khớp bộ lọc.`:'Chưa có tài khoản.';",
    )
    html = replace_once(
        html,
        "}).join('')||'<tr><td colspan=\"6\" class=\"muted\">Không có tài khoản phù hợp.</td></tr>';",
        "}).join('')||(adminUsers.length?'<tr><td colspan=\"6\" class=\"muted\">Không có tài khoản khớp bộ lọc. <button type=\"button\" class=\"btn ghost\" data-action=\"clear-admin-filters\" onclick=\"resetAdminFilters()\">Xóa bộ lọc để xem tất cả</button></td></tr>':'<tr><td colspan=\"6\" class=\"muted\">Chưa có tài khoản.</td></tr>');",
    )
    frontend.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    apply_patch(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app"))
