.PHONY: up down test lint migrate seed reset web-prod

up:
	@test -f .env || cp .env.example .env
	docker compose up --build -d

down:
	docker compose down

reset:
	@echo "This will remove all containers, volumes, and data. Continue? [y/N]"
	@read ans && [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]
	docker compose down -v

test:
	docker compose exec -T api pytest -v
	docker run --rm --network phishing-attack-simulator_dev -v $(PWD)/frontend:/app -w /app mcr.microsoft.com/playwright:v1.48.2-jammy sh -c "cd /app && npx playwright test --reporter=line"

lint:
	docker compose exec -T api ruff check .
	docker compose exec -T api mypy app
	cd frontend && npm run lint
	cd frontend && npx tsc --noEmit

migrate:
	docker compose exec -T -e PYTHONPATH=/app api alembic upgrade head

seed:
	docker compose exec -T -e APP_ENV=development -e PYTHONPATH=/app api python -m app.scripts.seed_dev

web-prod:
	docker compose up --build -d web-prod
