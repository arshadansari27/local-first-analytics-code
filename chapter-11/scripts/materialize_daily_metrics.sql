-- Materialize Daily Metrics for Performance
-- Run once daily via cron to pre-compute aggregates

CREATE OR REPLACE TABLE curated.daily_metrics AS
SELECT
    DATE_TRUNC('day', order_date) as date,
    SUM(total_amount) as revenue,
    COUNT(*) as orders,
    COUNT(DISTINCT customer_id) as active_customers
FROM curated.orders
GROUP BY 1;

-- Add index for faster lookups
-- CREATE INDEX idx_daily_metrics_date ON curated.daily_metrics(date);
