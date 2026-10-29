.PHONY: up down test lint migrate seed unlock-user reset web-prod

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
	docker run --rm --network phishing-attack-simulator_dev -v $(PWD)/frontend:/app -w /app mcr.microsoft.com/playwright:v1.64.1-jammy sh -c "cd /app && npx playwright test --reporter=line"

lint:
	docker compose exec -T api ruff check .
	docker compose exec -T api mypy app
	docker compose exec -T web sh -c "cd /app && npm run lint && npx tsc --noEmit"

migrate:
	docker compose exec -T -e PYTHONPATH=/app api alembic upgrade head

seed:
	docker compose exec -T -e APP_ENV=development -e PYTHONPATH=/app api python -m app.scripts.seed_dev

unlock-user:
	@test -n "$(EMAIL)" || { echo "ERROR: EMAIL is required (usage: make unlock-user EMAIL=<email>)"; exit 1; }
	docker compose exec -T -e PYTHONPATH=/app -e UNLOCK_EMAIL=$(EMAIL) api python -m app.scripts.unlock_user

web-prod:
	docker compose up --build -d web-prod
