.PHONY: backend frontend test build docker

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/pytest -q

build:
	cd frontend && npm run build

docker:
	docker compose up --build
