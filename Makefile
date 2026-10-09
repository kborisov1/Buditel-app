-include .env
export

BACKEND = cd backend && uv run
STAMP = $(shell date +%Y%m%d-%H%M%S)

.PHONY: install db backend frontend types test lint backup seed

install:
	cd backend && uv sync
	cd frontend && npm install

db:
	docker compose up -d db

backend:
	$(BACKEND) python manage.py migrate
	$(BACKEND) python manage.py runserver 127.0.0.1:8000

frontend:
	cd frontend && npm run dev

types:
	$(BACKEND) python manage.py export_openapi_schema --api config.api.api --output openapi.json
	cd frontend && npm run types

test:
	$(BACKEND) pytest
	cd frontend && npm test

lint:
	$(BACKEND) ruff check .
	$(BACKEND) mypy .
	cd frontend && npm run lint && npm run typecheck

backup:
	mkdir -p backups
	docker compose exec -T db pg_dump -U $(POSTGRES_USER) $(POSTGRES_DB) > backups/db-$(STAMP).sql
	@if [ -d media ]; then cp -R media backups/media-$(STAMP); fi

seed:
	$(BACKEND) python manage.py loaddata sample
