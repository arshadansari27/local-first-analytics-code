# Chapter 7: Data Quality Gates
# Makefile for running quality validation pipelines

# Use the repo-level venv if present; falls back to system python.
PYTHON ?= $(if $(wildcard ../../.venv/bin/python),../../.venv/bin/python,python3)

.PHONY: help validate quality-report clean

help: ## Show this help message
	@echo "Chapter 7: Data Quality Gates"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

validate: ## Run all quality checks
	@echo "Running quality checks..."
	$(PYTHON) validate_orders.py
	@echo "[OK] Quality pipeline complete"

quality-report: ## Generate quality dashboard CSV from quality_log
	@echo "Generating quality report..."
	$(PYTHON) -c "import duckdb; \
con = duckdb.connect('analytics.duckdb'); \
con.execute(\"\"\"COPY ( \
    SELECT check_name, check_type, COUNT(*) AS failure_count, MAX(run_at) AS last_failure \
    FROM quality_log WHERE failing_rows > 0 GROUP BY 1, 2 \
) TO 'quality_report.csv' (HEADER, DELIMITER ',')\"\"\")"
	@echo "Report: quality_report.csv"

clean: ## Clean generated files
	rm -f analytics.duckdb analytics.duckdb.wal
	rm -f quality_report.csv
	rm -rf staging/ raw/
	@echo "[OK] Cleaned up generated files"
