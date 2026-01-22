.PHONY: help build up down restart logs reindex clean add

help:
	@echo "CodeRAG Makefile Commands:"
	@echo "  make build      - Build Docker images"
	@echo "  make up         - Start all services"
	@echo "  make down       - Stop all services"
	@echo "  make restart    - Restart all services"
	@echo "  make logs       - Show logs from all services"
	@echo "  make reindex    - Reindex a project (usage: make reindex PROJECT_ID=1)"
	@echo "  make add        - Add project path mount (usage: make add BASE_PATH=/path/to/project)"
	@echo "  make clean      - Remove all containers and volumes"
	@echo "  make init-db    - Initialize database"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

reindex:
	@if [ -z "$(PROJECT_ID)" ]; then \
		echo "Usage: make reindex PROJECT_ID=1"; \
		exit 1; \
	fi
	curl -X POST http://localhost:8000/api/projects/$(PROJECT_ID)/reindex

clean:
	docker-compose down -v
	docker system prune -f

init-db:
	docker-compose exec backend python -c "from app.core.database import init_db; init_db()"

add:
	@if [ -z "$(BASE_PATH)" ]; then \
		echo "Usage: make add BASE_PATH=/path/to/project"; \
		exit 1; \
	fi
	@python3 scripts/add_project_path.py "$(BASE_PATH)"

