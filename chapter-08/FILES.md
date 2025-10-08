# Chapter 8 Code Files

Complete code examples extracted from Chapter 8: Orchestration Progression.

## Structure

```
chapter-08/
├── README.md                          # Comprehensive guide and documentation
├── FILES.md                           # This file
├── .gitignore                         # Git ignore patterns
├── Makefile                           # Level 1: Make orchestration
├── Makefile.multi-source              # Multi-source ETL (Make version)
├── docker-compose.yml                 # Service stack (Prefect, Temporal, n8n)
│
├── Orchestration Levels
│   ├── prefect_pipeline.py            # Level 2: Prefect with retries & caching
│   ├── dagster_pipeline.py            # Level 3: Asset-centric Dagster
│   ├── temporal_workflow.py           # Level 4: Durable workflows
│   ├── temporal_worker.py             # Temporal worker process
│   └── temporal_run.py                # Execute Temporal workflows
│
├── Multi-Source ETL Examples
│   ├── multi_source_etl_prefect.py    # Prefect version
│   └── multi_source_etl_dagster.py    # Dagster version
│
├── scripts/                           # Reusable scripts
│   ├── fetch_orders.py                # API pagination example
│   ├── run_pipeline.sh                # Cron wrapper with logging
│   ├── quality.py                     # Quality checks
│   ├── transform.sql                  # DuckDB transformations
│   └── compute_revenue.sql            # Revenue aggregation
│
├── quality/                           # Quality checks
│   └── orders_checks.sql              # Business rules validation
│
├── Tests
│   └── test_dagster_assets.py         # Dagster asset tests
│
└── Notebooks
    └── chapter_08_orchestration.ipynb # Interactive walkthrough
```

## Quick Start

### 1. Level 1: Make + cron

```bash
# Run full pipeline
make all

# Run specific targets
make extract
make transform
make quality
```

### 2. Level 2: Prefect

```bash
# Install
pip install prefect prefect-duckdb

# Run directly
python prefect_pipeline.py

# With UI
prefect server start  # In separate terminal
python prefect_pipeline.py
```

### 3. Level 3: Dagster

```bash
# Install
pip install dagster dagster-webserver dagster-polars dagster-duckdb

# Run
python dagster_pipeline.py

# With UI
dagster dev
```

### 4. Level 4: Temporal

```bash
# Start server
temporal server start-dev  # In separate terminal

# Start worker
python temporal_worker.py  # In separate terminal

# Execute workflow
python temporal_run.py ingestion
```

## Multi-Source ETL

The same pipeline implemented in three orchestration levels:

```bash
# Make version
make -f Makefile.multi-source all

# Prefect version
python multi_source_etl_prefect.py

# Dagster version
python multi_source_etl_dagster.py
```

## Files by Category

### Core Orchestration (Required)
- `prefect_pipeline.py` - Level 2 orchestration
- `dagster_pipeline.py` - Level 3 orchestration
- `temporal_workflow.py` - Level 4 orchestration

### Multi-Source Examples (Demonstrates progression)
- `multi_source_etl_prefect.py` - Parallel extraction with retries
- `multi_source_etl_dagster.py` - Type-safe asset pipeline

### Makefiles (Level 1)
- `Makefile` - Basic pipeline orchestration
- `Makefile.multi-source` - Multi-source ETL example

### Scripts (Supporting)
- `scripts/fetch_orders.py` - API pagination
- `scripts/run_pipeline.sh` - Cron wrapper
- `scripts/quality.py` - Data quality checks
- `scripts/transform.sql` - DuckDB transformations
- `scripts/compute_revenue.sql` - Revenue metrics

### Configuration
- `docker-compose.yml` - Service stack
- `.gitignore` - Git ignore patterns

### Documentation
- `README.md` - Complete guide
- `FILES.md` - This file

### Interactive
- `chapter_08_orchestration.ipynb` - Jupyter notebook walkthrough

### Tests
- `test_dagster_assets.py` - Dagster asset testing

## Dependencies

### Core
```bash
pip install polars duckdb pandera
```

### Level 2: Prefect
```bash
pip install prefect prefect-duckdb
```

### Level 3: Dagster
```bash
pip install dagster dagster-webserver dagster-polars dagster-duckdb
```

### Level 4: Temporal
```bash
pip install temporalio
brew install temporal  # or: curl -sSf https://temporal.download/cli.sh | sh
```

### Optional
```bash
pip install jupyter httpx paramiko minio  # For examples
```

## Learning Path

1. **Start with Jupyter notebook** (`chapter_08_orchestration.ipynb`)
   - Interactive examples of all levels
   - Side-by-side comparisons

2. **Run Make pipeline** (`make all`)
   - Understand dependency-based execution
   - See Make's simplicity

3. **Try Prefect** (`python prefect_pipeline.py`)
   - Add retries and caching
   - Run tasks in parallel

4. **Explore Dagster** (`python dagster_pipeline.py`)
   - Asset-centric thinking
   - Type-safe schemas

5. **Study multi-source ETL**
   - Compare implementations across levels
   - Understand when to graduate

## Key Concepts Demonstrated

### Make + cron (Level 1)
- Dependency tracking
- Incremental builds
- Error handling
- Logging

### Prefect (Level 2)
- Automatic retries with backoff
- Result caching
- Parallel task execution
- Local-first deployment

### Dagster (Level 3)
- Asset definitions
- Type-safe schemas with Pandera
- Automatic lineage
- Testing without execution

### Temporal (Level 4)
- Durable workflows
- Long-running processes
- Human-in-the-loop
- Crash recovery

## Decision Tree

```
Do you have >5 interdependent steps?
|-- NO -> Make + cron
+-- YES -> Do steps fail randomly?
    |-- NO -> Make + cron
    +-- YES -> Do you need type safety?
        |-- NO -> Prefect
        +-- YES -> Do workflows take >1 hour?
            |-- NO -> Dagster
            +-- YES -> Temporal
```

**Most readers will end up in the "Dagster" box.**

## Related Chapters

- Chapter 7: Data Quality Gates
- Chapter 9: Docker Compose packaging
- Chapter 10: Production deployment
