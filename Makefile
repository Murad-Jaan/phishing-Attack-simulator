.PHONY: up down test lint migrate seed

up:
	docker compose up --build -d

down:
	docker compose down -v

test:
	@echo "Running tests..."
	@cd backend && python -m pytest -v 2>&1 | tail -30 || true
	@cd frontend && npx playwright test 2>&1 | tail -30 || true

lint:
	@echo "Linting..."
	@cd backend && ruff check . 2>&1 | tail -20 || true
	@cd frontend && npm run lint 2>&1 | tail -20 || true

migrate:
	@echo "Running migrations..."
	@cd backend && alembic upgrade head

seed:
	@echo "Running dev seed..."
	@cd backend && python -m app.scripts.seed_dev
