from pathlib import Path

ROOT = Path("/app")
main_path = ROOT / "app" / "main.py"
frontend_path = ROOT / "app" / "static" / "index.html"

main = main_path.read_text(encoding="utf-8")
if "PHY_AI_PUBLIC_SECURITY_V1" not in main:
    main += r'''

# PHY_AI_PUBLIC_SECURITY_V1
@app.middleware("http")
async def phy_ai_public_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    path = request.url.path
    if path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    elif path == "/" or path.endswith(".html"):
        response.headers["Cache-Control"] = "no-cache"
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    if request.url.scheme == "https" or forwarded_proto.split(",")[0].strip() == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
'''
    main_path.write_text(main, encoding="utf-8")

html = frontend_path.read_text(encoding="utf-8")
if 'id="studentPrivacyNotice"' not in html:
    css = r'''
<style id="public-release-styles">
.student-privacy-note{margin:18px 0 0;padding:14px 15px;border:1px solid var(--border);border-radius:12px;background:#fffaf6;color:var(--muted);font-size:12px;line-height:1.65}
.student-privacy-note strong{display:block;color:var(--text);font-size:13px;margin-bottom:4px}
.student-privacy-note p{margin:4px 0}
.student-privacy-note details{margin-top:8px}
.student-privacy-note summary{cursor:pointer;font-weight:700;color:#a43e09}
</style>
'''
    if "</head>" not in html:
        raise SystemExit("HTML head marker missing for public release patch")
    html = html.replace("</head>", css + "\n</head>", 1)

    anchor = '''   </details>
  </article>
 </div>
</section>'''
    privacy = '''   </details>
   <div id="studentPrivacyNotice" class="student-privacy-note" role="note">
    <strong>Quyền riêng tư và AI</strong>
    <p>PHY-AI DIAGNOSE lưu tên đăng nhập, họ tên hiển thị, lớp, câu trả lời và kết quả học tập để tạo hồ sơ học tập và hỗ trợ giáo viên theo dõi tiến bộ. Hệ thống không yêu cầu email hoặc số điện thoại.</p>
    <details>
     <summary>Dữ liệu nào được gửi tới AI?</summary>
     <p>Khi học sinh nhập phần giải thích trong phiên chẩn đoán, AI chỉ nhận nội dung câu hỏi, câu trả lời và phần giải thích cần phân tích; không gửi họ tên hay tên đăng nhập. AI chỉ tạo bằng chứng gợi ý, không tự quyết định hồ sơ lỗi.</p>
    </details>
   </div>
  </article>
 </div>
</section>'''
    if anchor not in html:
        raise SystemExit("Student portal marker missing for privacy notice")
    html = html.replace(anchor, privacy, 1)
    frontend_path.write_text(html, encoding="utf-8")

print("Public release security/privacy patch applied")
