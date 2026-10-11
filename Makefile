run:
	uvicorn app.main:app --reload --port 8000

test:
	python scripts/validate_bank.py
	pytest -q

docker:
	docker compose up --build
