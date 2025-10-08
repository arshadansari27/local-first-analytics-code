-- transform.sql
-- DuckDB transformations for daily metrics

CREATE OR REPLACE TABLE metrics AS
SELECT
    DATE_TRUNC('day', timestamp) as date,
    COUNT(DISTINCT user_id) as daily_active_users,
    COUNT(*) as total_events,
    SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as purchases,
    SUM(CASE WHEN event_type = 'purchase' THEN amount ELSE 0 END) as revenue
FROM read_parquet('data/staging/*.parquet')
GROUP BY 1
ORDER BY 1 DESC;
