SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

# Phony targets
.PHONY: all extract transform quality report clean help setup

##@ General

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

setup: ## Create data directories
	@mkdir -p data/{raw,staging,curated} logs
	@echo "[OK] Directories created"

##@ Pipeline Targets

all: report ## Run full pipeline

extract: data/raw/api_data.json data/raw/db_export.csv ## Extract data from sources
	@echo "[OK] Extraction complete"

transform: data/curated/daily_metrics.parquet data/curated/user_cohorts.parquet ## Run transformations
	@echo "[OK] Transformations complete"

quality: transform ## Run quality checks
	python scripts/quality.py --data-dir data/curated
	@echo "[OK] Quality checks passed"

report: quality ## Generate report
	@echo "[OK] Report generated"

##@ Data Files

data/raw/api_data.json:
	@echo "Fetching API data..."
	@mkdir -p data/raw
	@# Simulate API fetch
	@echo '[{"id": 1, "value": 100}]' > $@

data/raw/db_export.csv:
	@echo "Exporting database..."
	@mkdir -p data/raw
	@# Simulate DB export
	@echo "id,name,value" > $@
	@echo "1,test,100" >> $@

data/staging/cleaned_data.parquet: data/raw/api_data.json data/raw/db_export.csv
	@echo "Cleaning data..."
	@mkdir -p data/staging
	python scripts/clean.py --input data/raw --output $@

data/curated/daily_metrics.parquet: data/staging/cleaned_data.parquet scripts/transform.sql
	@echo "Computing metrics..."
	@mkdir -p data/curated
	duckdb -c ".read scripts/transform.sql" \
		-c "COPY (SELECT * FROM metrics) TO '$@' (FORMAT PARQUET, COMPRESSION ZSTD)"

data/curated/user_cohorts.parquet: data/staging/cleaned_data.parquet
	@echo "Computing cohorts..."
	@mkdir -p data/curated
	@touch $@  # Placeholder

##@ Maintenance

clean: ## Remove generated files
	rm -rf data/staging/* data/curated/* logs/*
	@echo "[OK] Cleaned staging and curated data"

clean-all: clean ## Remove all data including raw
	rm -rf data/raw/*
	@echo "[OK] Cleaned all data"

##@ Validation

validate: ## Run all quality checks
	@echo "Running quality checks..."
	python scripts/quality.py
	duckdb analytics.duckdb < quality/orders_checks.sql
	@echo "[OK] Quality pipeline complete"

quality-report: ## Generate quality dashboard
	duckdb analytics.duckdb <<< "COPY ( \
	    SELECT \
	        check_name, \
	        check_type, \
	        COUNT(*) as failure_count, \
	        MAX(run_at) as last_failure \
	    FROM quality_log \
	    WHERE failing_rows > 0 \
	    GROUP BY 1, 2 \
	) TO 'bi/quality_report.csv' (HEADER, DELIMITER ',')"
	@echo "Report: bi/quality_report.csv"
