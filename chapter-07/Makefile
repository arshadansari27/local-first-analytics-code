# Chapter 7: Data Quality Gates
# Makefile for running quality validation pipelines

.PHONY: help validate quality-report clean

help: ## Show this help message
	@echo "Chapter 7: Data Quality Gates"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

validate: ## Run all quality checks
	@echo "Running quality checks..."
	python validate_orders.py
	duckdb analytics.duckdb < quality/orders_checks.sql
	@echo "[OK] Quality pipeline complete"

quality-report: ## Generate quality dashboard
	@echo "Generating quality report..."
	duckdb analytics.duckdb <<< "COPY ( \
	    SELECT \
	        check_name, \
	        check_type, \
	        COUNT(*) as failure_count, \
	        MAX(run_at) as last_failure \
	    FROM quality_log \
	    WHERE failing_rows > 0 \
	    GROUP BY 1, 2 \
	) TO 'quality_report.csv' (HEADER, DELIMITER ',')"
	@echo "Report: quality_report.csv"

clean: ## Clean generated files
	rm -f analytics.duckdb
	rm -f quality_report.csv
	rm -rf staging/
	@echo "[OK] Cleaned up generated files"
