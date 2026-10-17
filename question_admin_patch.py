"""Inject optional admin question bank without changing the protected 1,000-question bank."""
from pathlib import Path
from shutil import copyfile

main_path=Path("/app/app/main.py")
html_path=Path("/app/app/static/index.html")
for file in ("question_admin_store.py","question_admin_overlay.py"):
    copyfile(Path("/tmp")/file, Path("/app/app")/file)
copyfile(Path("/tmp/question_admin_ui.js"),Path("/app/app/static/question_admin_ui.js"))
main=main_path.read_text(encoding="utf-8")
if "@app.get(\"/api/admin/question-bank\")" in main:
    raise SystemExit("Question admin already installed")
if "@app.post(\"/api/tutor/start\")" not in main:
    raise SystemExit("Expected installed Socratic Tutor before question bank administration")
route_marker='@app.get("/api/ai/status")'
if main.count(route_marker)!=1:
    raise SystemExit("API insertion marker unavailable; refuse unsafe catch-all ordering")
routes=Path("/tmp/question_admin_api.py").read_text(encoding="utf-8")
main=main.replace(route_marker,routes+"\n\n"+route_marker,1)
main_path.write_text(main,encoding="utf-8")

html=html_path.read_text(encoding="utf-8")
if 'id="questionAdminRoot"' in html:
    raise SystemExit("Question admin UI already installed")
start=html.find('<section id="adminView"')
if start<0:raise SystemExit("Existing administrator section not found")
close=html.find("</section>",start)
if close<0:raise SystemExit("Administrator closing section not found")
panel=r'''
<div class="card" style="margin-top:14px">
  <button type="button" class="btn primary" onclick="qaOpen()">📚 Quản trị ngân hàng câu hỏi</button>
  <div class="small muted">Quản lí bản nháp, liên kết lỗi tư duy, nhập Excel, duyệt và công bố. Chỉ tài khoản Quản trị viên được phép sử dụng.</div>
</div>
<div id="questionAdminRoot" class="card" style="display:none;margin-top:14px">
  <div class="toolbar"><h2>Ngân hàng câu hỏi Vật lí 12</h2>
     <div class="actions"><button class="btn secondary" onclick="qaNew()">+ Thêm câu</button>
     <button class="btn secondary" onclick="qaRefresh()">Làm mới</button></div></div>
  <p id="qaMode" class="small muted"></p><p id="qaNotice" role="status" aria-live="polite"></p>
  <div class="grid2" style="margin:12px 0">
    <div class="field"><label>Tìm mã hoặc câu dẫn</label><input id="qaFind" type="search" placeholder="Nhập mã câu..." oninput="qaRefresh()"></div>
    <div class="field"><label>Lọc chương</label><select id="qaFilterChapter" onchange="qaRefresh()"></select></div>
    <div class="field"><label>Trạng thái</label><select id="qaFilterStatus" onchange="qaRefresh()">
      <option value="">Tất cả</option><option value="base">Ngân hàng chuẩn</option>
      <option value="draft">Bản nháp</option><option value="submitted">Chờ duyệt</option>
      <option value="published">Đã công bố</option><option value="archive_requested">Chờ duyệt xóa</option>
      <option value="archived">Đã ẩn/xóa</option></select></div>
    <div class="field"><label>Nhập Excel (.xlsx tối đa 3 MB, 300 câu/lần)</label>
       <input type="file" id="qaImport" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet">
       <div class="actions"><button class="btn secondary" type="button" onclick="qaTemplate()">Tải mẫu Excel</button>
       <button class="btn primary" type="button" onclick="qaImport()">Nhập bản nháp</button></div></div>
  </div>
  <div class="table"><table><thead><tr>
  <th>Mã</th><th>Chương/Bài</th><th>Dạng</th><th>Câu hỏi</th><th>Mã lỗi</th><th>Trạng thái</th><th>Thao tác</th>
  </tr></thead><tbody id="qaRows"></tbody></table></div>
  <div class="actions" style="margin-top:12px"><button id="qaPrev" class="btn ghost" onclick="qaPage(-1)">← Trước</button>
  <span id="qaPage"></span><button id="qaNext" class="btn ghost" onclick="qaPage(1)">Sau →</button></div>
  <div id="qaEditor" style="display:none;margin-top:25px;border-top:2px solid #e9eef3;padding-top:16px">
    <h3 id="qaEditorTitle">Thêm câu hỏi</h3>
    <div class="grid2">
      <div class="field"><label>Mã câu gốc (để sửa câu trong ngân hàng gốc; để trống nếu tạo mới)</label>
        <input id="qaSource" maxlength="80"></div>
      <div class="field"><label>Chương</label><select id="qaChapter" onchange="qaChapterChanged()"></select></div>
      <div class="field"><label>Bài học</label><select id="qaLesson" onchange="qaLessonChanged()"></select></div>
      <div class="field"><label>Dạng câu</label><select id="qaType" onchange="qaTypeChanged()">
       <option value="mcq">Trắc nghiệm nhiều lựa chọn</option>
       <option value="tf">Đúng/Sai (4 mệnh đề)</option>
       <option value="short">Trả lời ngắn</option></select></div>
    </div>
    <div class="field"><label>Câu dẫn</label><textarea id="qaPrompt" rows="4" maxlength="2500"></textarea></div>
    <div class="field"><label>Ngữ cảnh (không bắt buộc)</label><textarea id="qaContext" rows="2"></textarea></div>
    <div id="qaMcqFields">
      <div class="field"><label>4 phương án A–D (mỗi dòng một phương án)</label><textarea id="qaOptions" rows="5"></textarea></div>
      <div class="field"><label>Đáp án</label><select id="qaMcqAnswer"><option>A</option><option>B</option><option>C</option><option>D</option></select></div>
    </div>
    <div id="qaTfFields" style="display:none"><div class="field"><label>4 mệnh đề dạng JSON: text, answer (true/false), explain</label>
    <textarea id="qaStatements" rows="9" spellcheck="false"></textarea></div></div>
    <div id="qaShortFields" style="display:none" class="grid2">
      <div class="field"><label>Đáp án số</label><input id="qaShortAnswer"></div>
      <div class="field"><label>Dung sai</label><input id="qaTolerance" value="0.01"></div>
      <div class="field"><label>Đơn vị (nếu có)</label><input id="qaUnit"></div>
    </div>
    <div class="field"><label>Giải thích/lời giải chi tiết</label><textarea id="qaExplain" rows="4"></textarea></div>
    <div class="grid2">
       <div class="field"><label>Gắn mã lỗi tư duy (thuộc đúng bài)</label><select id="qaError"></select></div>
       <div class="field"><label><input type="checkbox" id="qaDiagnostic"> Dùng làm câu chẩn đoán (bắt buộc mã lỗi)</label></div>
    </div>
    <button id="qaSaveBtn" class="btn primary" type="button" onclick="qaSave()">Lưu bản nháp</button>
    <p class="small muted">Bản nháp không tự xuất hiện trong phiên học. Cần Gửi duyệt → Duyệt để tạo phiên bản công bố. Xóa/ẩn cũng cần duyệt.</p>
  </div>
</div>
'''
html=html[:close]+panel+html[close:]
if "</body>" not in html:raise SystemExit("HTML closing body marker not found")
html=html.replace("</body>",'<script src="/static/question_admin_ui.js" defer></script></body>',1)
html_path.write_text(html,encoding="utf-8")
print("Optional question bank administrator routes/UI installed; both flags default OFF.")
