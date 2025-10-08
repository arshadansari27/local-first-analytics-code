-- compute_revenue.sql
-- Daily revenue aggregation for multi-source ETL

COPY (
    SELECT
        DATE_TRUNC('day', order_date) as date,
        COUNT(*) as order_count,
        COUNT(DISTINCT customer_id) as unique_customers,
        SUM(total) as total_revenue,
        AVG(total) as avg_order_value,
        MAX(total) as max_order_value
    FROM read_parquet('data/curated/orders.parquet')
    GROUP BY 1
    ORDER BY 1 DESC
) TO 'data/curated/daily_revenue.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
