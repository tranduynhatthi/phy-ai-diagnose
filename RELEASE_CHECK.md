# Release check — 2026-10-11

Đã chạy trực tiếp trong môi trường build:

- `python scripts/validate_bank.py` → PASS.
  - total = 1000
  - Chương I = 250
  - Chương II = 250
  - Chương III = 250
  - Chương IV = 250
  - schema issues = 0
- `pytest -q tests/test_api.py` → 1 passed.
  - health
  - teacher bootstrap/login
  - create class
  - student register + join class
  - start practice
  - answer + finish practice
  - create adaptive exam
  - exam structure = 18 + 4 + 6
  - answer keys are not exposed in exam payload
- JavaScript frontend → `node --check` PASS.
- Production smoke test with Uvicorn:
  - `GET /api/health` = HTTP 200
  - `GET /` = HTTP 200

Chưa kiểm tra trong Docker container vì runtime hiện tại không có Docker daemon. Dockerfile tuân theo chuẩn container FastAPI thông thường và app đã smoke-test trực tiếp bằng Uvicorn.
