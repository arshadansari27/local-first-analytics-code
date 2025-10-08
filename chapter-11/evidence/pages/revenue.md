# Revenue Dashboard

Last updated: {new Date().toISOString().split('T')[0]}

## Monthly Performance

```sql monthly_revenue
SELECT
    DATE_TRUNC('month', order_date) as month,
    SUM(total_amount) as revenue,
    COUNT(DISTINCT customer_id) as customers,
    SUM(total_amount) / COUNT(DISTINCT customer_id) as avg_customer_value
FROM curated.orders
WHERE order_date >= CURRENT_DATE - INTERVAL 12 MONTH
GROUP BY 1
ORDER BY 1;
```

<LineChart
    data={monthly_revenue}
    x=month
    y=revenue
    yAxisTitle="Revenue ($)"
/>

### Key Metrics (Last 30 Days)

```sql recent_metrics
SELECT
    SUM(total_amount) as total_revenue,
    COUNT(*) as total_orders,
    SUM(total_amount) / COUNT(*) as avg_order_value
FROM curated.orders
WHERE order_date >= CURRENT_DATE - INTERVAL 30 DAY;
```

<BigValue
    data={recent_metrics}
    value=total_revenue
    fmt='$#,##0'
/>
<BigValue
    data={recent_metrics}
    value=total_orders
    fmt='#,##0'
/>
<BigValue
    data={recent_metrics}
    value=avg_order_value
    fmt='$#,##0.00'
/>

## Top Products

```sql top_products
SELECT
    product_name,
    SUM(quantity) as units_sold,
    SUM(total_amount) as revenue
FROM curated.order_items
JOIN curated.products USING (product_id)
WHERE order_date >= CURRENT_DATE - INTERVAL 30 DAY
GROUP BY 1
ORDER BY revenue DESC
LIMIT 10;
```

<DataTable data={top_products} />
