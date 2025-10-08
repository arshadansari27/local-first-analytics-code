# Chapter 11 Code Files

Complete code examples extracted from Chapter 11: BI Without the Bloat.

## Overview

This chapter demonstrates local-first Business Intelligence with Evidence.dev (reports as code) and Metabase (ad-hoc analytics)—eliminating $400+/month BI subscriptions while maintaining full functionality.

## Structure

```
chapter-11/
├── Evidence Configuration & Reports
│   ├── evidence/sources/duckdb.yaml
│   └── evidence/pages/
│       ├── revenue.md
│       ├── category_drilldown.md
│       └── data_quality.md
│
├── Scripts
│   ├── scripts/export_to_sqlite_for_metabase.py
│   └── scripts/materialize_daily_metrics.sql
│
├── Docker & Deployment
│   ├── docker/compose.yaml
│   ├── docker/compose.production.yaml
│   └── docker/Caddyfile
│
├── Automation & Config
│   ├── Makefile
│   └── .gitignore
│
└── Documentation & Interactive
    ├── README.md
    ├── FILES.md (this file)
    └── chapter_11_bi_without_bloat.ipynb
```

## File Descriptions

### Evidence Reports

#### `evidence/sources/duckdb.yaml`
**DuckDB connection configuration**
- Points Evidence to local DuckDB database
- Path: `../../data/curated/analytics.duckdb`
- Enables zero-copy querying of Parquet data

#### `evidence/pages/revenue.md`
**Revenue dashboard** (from chapter Example 1)
- Monthly revenue trend line chart
- Key metrics cards (total revenue, orders, AOV)
- Top products table
- SQL queries embedded in markdown

**Features:**
```markdown
<LineChart data={monthly_revenue} x=month y=revenue />
<BigValue data={recent_metrics} value=total_revenue fmt='$#,##0' />
<DataTable data={top_products} />
```

#### `evidence/pages/category_drilldown.md`
**Parameterized category analysis** (from chapter Advanced section)
- Dropdown selector for categories
- Weekly revenue trend
- SQL parameters: `${inputs.category}`

**Features:**
```markdown
<Dropdown name=category>
    <DropdownOption value="Electronics" />
</Dropdown>
```

#### `evidence/pages/data_quality.md`
**Data quality scorecard** (from chapter Real Example)
- Pipeline health monitoring
- Quality checks (nulls, negative prices, future dates)
- Conditional alerts
- Freshness indicators

**Features:**
- Color-coded health indicators
- Alert components for failures
- Real-time quality metrics

### Scripts

#### `scripts/export_to_sqlite_for_metabase.py`
**DuckDB to SQLite export** (from chapter Metabase section)

Metabase doesn't natively support DuckDB, so this script exports the database to SQLite format for compatibility.

**Usage:**
```bash
python3 scripts/export_to_sqlite_for_metabase.py
# or
make export-sqlite
```

**Output:** `data/curated/metabase_export.db`

#### `scripts/materialize_daily_metrics.sql`
**Performance optimization** (from chapter Bonus section)

Pre-computes daily aggregates for faster Evidence queries.

**SQL:**
```sql
CREATE OR REPLACE TABLE curated.daily_metrics AS
SELECT
    DATE_TRUNC('day', order_date) as date,
    SUM(total_amount) as revenue,
    COUNT(*) as orders,
    COUNT(DISTINCT customer_id) as active_customers
FROM curated.orders
GROUP BY 1;
```

**Usage:**
```bash
make materialize
# or
duckdb data/curated/analytics.duckdb < scripts/materialize_daily_metrics.sql
```

**Automate with cron:**
```bash
0 1 * * * cd /project && make materialize
```

### Docker & Deployment

#### `docker/compose.yaml`
**Local BI stack** (from chapter Setup sections)

Runs Evidence and Metabase in Docker containers.

**Services:**
- **Evidence**: Port 3000, Node.js dev server
- **Metabase**: Port 3001, Java-based analytics

**Usage:**
```bash
docker compose -f docker/compose.yaml up -d
```

#### `docker/compose.production.yaml`
**Production deployment** (from chapter Pattern 2)

Adds Caddy reverse proxy for HTTPS.

**Additional service:**
- **Caddy**: Ports 80/443, automatic HTTPS

**Usage:**
```bash
docker compose -f docker/compose.production.yaml up -d
```

#### `docker/Caddyfile`
**Reverse proxy configuration** (from chapter Pattern 2)

Routes domain names to services with automatic HTTPS.

```
evidence.yourdomain.com {
    reverse_proxy localhost:3000
}

metabase.yourdomain.com {
    reverse_proxy localhost:3001
}
```

### Automation

#### `Makefile`
**Common BI operations**

```bash
make setup             # Install Evidence
make evidence          # Start Evidence dev
make metabase          # Start Metabase
make up                # Start all services
make export-sqlite     # Export for Metabase
make materialize       # Pre-compute metrics
make clean             # Remove all data
```

**Help:**
```bash
make help  # Show all targets
```

### Documentation

#### `README.md`
**Comprehensive guide** including:
- Quick start for Evidence and Metabase
- Example reports walkthrough
- Decision matrix (Evidence vs Metabase)
- 3 deployment patterns
- Performance optimization
- Common workflows
- Component reference
- Troubleshooting

#### `chapter_11_bi_without_bloat.ipynb`
**Interactive Jupyter notebook**
- Generate sample e-commerce data
- Create DuckDB database
- Test all dashboard queries
- Export to SQLite
- Performance comparison (raw vs materialized)
- Parameterized query examples

## Usage Patterns

### Pattern 1: Localhost Only

```bash
# Terminal 1
make evidence

# Terminal 2
make metabase
```

No network exposure. Solo developer.

### Pattern 2: Docker Compose (Team)

```bash
make up
```

Evidence: http://localhost:3000
Metabase: http://localhost:3001

### Pattern 3: VPS Production

```bash
docker compose -f docker/compose.production.yaml up -d
```

With Caddy for HTTPS:
- evidence.yourdomain.com
- metabase.yourdomain.com

**Cost: $5/month VPS** (vs $400/month Tableau)

### Pattern 4: Static + On-Demand

```bash
# Build Evidence static
cd evidence && npm run build

# Deploy to Netlify (free)
# Run Metabase only when needed
docker compose up -d metabase
```

## Decision Matrix

| Use Case | Tool | Why |
|----------|------|-----|
| Weekly exec report | Evidence | Version-controlled |
| Ad-hoc questions | Metabase | Self-service |
| Public dashboard | Evidence | Static, fast |
| Data validation | Metabase | Quick drill-downs |
| Automated reports | Evidence + cron | PDF generation |
| Team collaboration | Metabase | Permissions |

## Component Reference

### Evidence Charts

```markdown
<LineChart data={query} x=column_x y=column_y />
<BarChart data={query} x=category y=value />
<DataTable data={query} />
<BigValue data={query} value=metric fmt='$#,##0' />
```

### Evidence Inputs

```markdown
<Dropdown name=var title="Select">
    <DropdownOption value="Option1" />
</Dropdown>

<DateRange name=date_range />
<TextInput name=search />
```

### Evidence Alerts

```markdown
{#if condition}
  <Alert status=warning>Message</Alert>
{/if}
```

## Performance Optimization

### Materialize Aggregates

For frequently-queried metrics:

1. Run `make materialize` daily (via cron)
2. Evidence queries pre-computed table
3. Instant response instead of full scan

**Speedup:** 10-100x depending on data size

### Query Optimization

- Use `DATE_TRUNC` for time bucketing
- Pre-filter with `WHERE` before joins
- Limit result sets with `LIMIT`
- Partition Parquet by date

## Cost Comparison

| Metric | Traditional BI | Local-First |
|--------|----------------|-------------|
| Monthly cost | $400+ | $0-5 |
| Setup time | Days | 30 min |
| Query latency | 2-5s | <100ms |
| User limits | 5-10 | Unlimited |
| Version control | ❌ | ✅ |
| Offline | ❌ | ✅ |

## Troubleshooting

### Evidence Won't Start

```bash
cd evidence
rm -rf node_modules package-lock.json
npm install
```

### Metabase Can't Connect

Export to SQLite:
```bash
make export-sqlite
```

Then in Metabase:
- Add database → SQLite
- File: `/data/curated/metabase_export.db`

### Data Not Updating

Re-export from DuckDB:
```bash
make export-sqlite
```

### Port Conflicts

Edit `docker/compose.yaml`:
```yaml
ports:
  - "3002:3000"  # Change host port
```

## Key Takeaways

1. **Evidence = Reports as Code** - Version-controlled, Git-reviewed dashboards
2. **Metabase = Self-Service** - Non-technical users can explore without SQL
3. **Zero per-user fees** - Unlimited users for $0-5/month
4. **Local-first = Fast** - <100ms queries vs cloud 2-5s
5. **Materialized views** - Pre-compute for 10-100x speedup
6. **Static builds** - Evidence compiles to static HTML (free hosting)

## Related Files

- **Chapter 7:** Quality gates ensure dashboard accuracy
- **Chapter 8:** Orchestrate report generation with Prefect
- **Chapter 9:** Containerize BI stack with Docker
- **Chapter 12:** Add natural language querying with LLMs

## Next Steps

1. Install Evidence: `make setup`
2. Start services: `make up`
3. Generate sample data with Jupyter notebook
4. Customize Evidence pages for your use cases
5. Set up Metabase for team self-service
6. Deploy to VPS with Caddy
7. Automate metric materialization

## Success Metrics

All code from Chapter 11 extracted:
- ✅ Evidence configuration and 3 example reports
- ✅ Metabase Docker setup
- ✅ SQLite export script
- ✅ Daily metrics materialization
- ✅ 3 deployment patterns (local, Docker, VPS)
- ✅ Caddy reverse proxy config
- ✅ Comprehensive Makefile
- ✅ Interactive Jupyter notebook
- ✅ Complete documentation

**Result: $0-5/month BI stack replacing $400/month SaaS**
