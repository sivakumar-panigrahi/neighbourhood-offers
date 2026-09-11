.PHONY: help test test-backend build-frontend run-backend run-frontend seed docker-up docker-down

help:
	@echo "Neighbourhood Offers - Development Commands:"
	@echo "  make test           - Run full test suite"
	@echo "  make test-backend   - Run pytest regression tests"
	@echo "  make build-frontend - Build frontend production bundle"
	@echo "  make seed           - Seed database with deterministic demo data"
	@echo "  make docker-up      - Start full application in Docker"
	@echo "  make docker-down    - Stop Docker containers"

test: test-backend build-frontend

test-backend:
	cd backend && pytest -v

build-frontend:
	cd frontend && npm run build

seed:
	cd backend && python -m scripts.seed

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down
