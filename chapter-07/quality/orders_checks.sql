-- quality/orders_checks.sql
-- Chapter 7: Business Rules Validation
-- Tier 2: DuckDB-based logical validation checks

CREATE TABLE IF NOT EXISTS quality_log (
    check_name VARCHAR,
    check_type VARCHAR,
    failing_rows BIGINT,
    check_query TEXT,
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Check 1: Orders without matching customers
-- Tests referential integrity
INSERT INTO quality_log (check_name, check_type, failing_rows, check_query)
SELECT
    'orphan_orders' as check_name,
    'referential_integrity' as check_type,
    COUNT(*) as failing_rows,
    'SELECT * FROM orders WHERE customer_id NOT IN (SELECT id FROM customers)' as check_query
FROM staging.orders o
WHERE NOT EXISTS (
    SELECT 1 FROM staging.customers c WHERE c.id = o.customer_id
);

-- Check 2: Revenue anomalies (>3 std devs from daily mean)
-- Statistical outlier detection
WITH daily_revenue AS (
    SELECT
        DATE_TRUNC('day', order_date) as day,
        SUM(amount) as revenue
    FROM staging.orders
    GROUP BY 1
),
stats AS (
    SELECT
        AVG(revenue) as mean,
        STDDEV(revenue) as std
    FROM daily_revenue
)
INSERT INTO quality_log (check_name, check_type, failing_rows, check_query)
SELECT
    'revenue_anomaly' as check_name,
    'statistical_outlier' as check_type,
    COUNT(*) as failing_rows,
    'Daily revenue >3σ from mean' as check_query
FROM daily_revenue d, stats s
WHERE ABS(d.revenue - s.mean) > 3 * s.std;

-- Check 3: Future-dated orders
-- Temporal logic validation
INSERT INTO quality_log (check_name, check_type, failing_rows, check_query)
SELECT
    'future_orders' as check_name,
    'temporal_logic' as check_type,
    COUNT(*) as failing_rows,
    'SELECT * FROM orders WHERE order_date > CURRENT_DATE' as check_query
FROM staging.orders
WHERE order_date > CURRENT_DATE;
