.PHONY: help setup evidence metabase up down logs clean export-sqlite materialize

##@ General

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

setup: ## Install Evidence dependencies
	@echo "[INFO] Setting up Evidence..."
	cd evidence && npm init -y && npm install @evidence-dev/evidence
	@echo "[OK] Evidence ready"

##@ BI Services

evidence: ## Start Evidence dev server
	cd evidence && npm run dev

evidence-build: ## Build static Evidence site
	cd evidence && npm run build
	@echo "[OK] Static site in evidence/build/"

metabase: ## Start Metabase in Docker
	docker compose -f docker/compose.yaml up -d metabase
	@echo "[OK] Metabase at http://localhost:3001"

up: ## Start all BI services
	docker compose -f docker/compose.yaml up -d
	@echo "[OK] Evidence: http://localhost:3000"
	@echo "[OK] Metabase: http://localhost:3001"

down: ## Stop all BI services
	docker compose -f docker/compose.yaml down

restart: down up ## Restart all services

##@ Logs & Monitoring

logs: ## Follow all service logs
	docker compose -f docker/compose.yaml logs -f

logs-evidence: ## Follow Evidence logs
	docker compose -f docker/compose.yaml logs -f evidence

logs-metabase: ## Follow Metabase logs
	docker compose -f docker/compose.yaml logs -f metabase

##@ Data Management

export-sqlite: ## Export DuckDB to SQLite for Metabase
	python3 scripts/export_to_sqlite_for_metabase.py

materialize: ## Materialize daily metrics (run daily)
	duckdb data/curated/analytics.duckdb < scripts/materialize_daily_metrics.sql
	@echo "[OK] Daily metrics materialized"

##@ Maintenance

clean: ## Stop services and remove volumes
	docker compose -f docker/compose.yaml down -v
	@echo "[OK] Cleaned all data"

clean-evidence: ## Remove Evidence node_modules
	rm -rf evidence/node_modules evidence/package-lock.json
	@echo "[OK] Evidence cleaned"

rebuild: down clean up ## Full rebuild

##@ Production

prod-up: ## Start production stack with Caddy
	docker compose -f docker/compose.production.yaml up -d
	@echo "[OK] Production stack running"

prod-down: ## Stop production stack
	docker compose -f docker/compose.production.yaml down

##@ Access

open-evidence: ## Open Evidence in browser
	open http://localhost:3000

open-metabase: ## Open Metabase in browser
	open http://localhost:3001
