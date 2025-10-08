.PHONY: up down shell logs clean prefect evidence minio help

##@ General

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Docker Stack

up: ## Start all services
	docker compose up -d
	@echo "[OK] Stack running"
	@echo "Prefect:  http://localhost:4200"
	@echo "MinIO:    http://localhost:9001"
	@echo "Evidence: http://localhost:3000"

down: ## Stop all services
	docker compose down

restart: down up ## Restart all services

##@ Container Access

shell: ## Open bash shell in analytics container
	docker compose exec analytics bash

logs: ## Follow logs from all services
	docker compose logs -f

logs-analytics: ## Follow analytics container logs
	docker compose logs -f analytics

logs-prefect: ## Follow Prefect logs
	docker compose logs -f prefect

logs-minio: ## Follow MinIO logs
	docker compose logs -f minio

##@ Maintenance

clean: ## Stop and remove all containers and volumes
	docker compose down -v
	docker system prune -f

rebuild: ## Rebuild analytics container from scratch
	docker compose build --no-cache analytics
	docker compose up -d --force-recreate analytics

##@ Services

prefect: ## Run Prefect flow (use FLOW=flowname)
	docker compose exec analytics bash -c "cd /workspace/etl/flows && python3 $$FLOW.py"

evidence: ## Open Evidence in browser
	open http://localhost:3000

minio: ## Open MinIO console in browser
	open http://localhost:9001

##@ Development

dev: ## Start with dev overrides
	docker compose -f docker-compose.yaml -f docker-compose.dev.yaml --env-file .env.dev up -d

staging: ## Start with staging overrides
	docker compose -f docker-compose.yaml -f docker-compose.staging.yaml --env-file .env.staging up -d

##@ Testing

test: ## Run tests inside container
	docker compose exec analytics pytest /workspace/tests

test-minio: ## Test MinIO connectivity
	docker compose exec analytics python3 /workspace/examples/minio_setup.py

test-duckdb: ## Test DuckDB installation
	docker compose exec analytics python3 -c "import duckdb; print(duckdb.query('SELECT 42 as answer').fetchall())"

##@ Multi-Environment

minimal: ## Start minimal stack (analytics only)
	docker compose -f docker-compose.minimal.yaml up -d

with-minio: ## Start with MinIO
	docker compose -f docker-compose.minio.yaml up -d

full: up ## Start full stack (alias for up)
