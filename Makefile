.PHONY: help format lint typecheck test build up down logs migrate migration
help: ; @echo "make format lint typecheck test build up down logs migrate migration"
format: ; cd backend && ruff format app tests
lint: ; cd backend && ruff check app tests && ruff format --check app tests; cd frontend && npm run lint
typecheck: ; cd backend && mypy app; cd frontend && npm run typecheck
test: ; cd backend && pytest; cd frontend && npm run test
build: ; cd frontend && npm run build
up: ; docker compose -f deployment/docker-compose.yml up --build
down: ; docker compose -f deployment/docker-compose.yml down
logs: ; docker compose -f deployment/docker-compose.yml logs -f
migrate: ; cd backend && alembic upgrade head
migration: ; cd backend && alembic revision -m "$(name)"
