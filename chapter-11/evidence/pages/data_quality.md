# Data Quality Scorecard

Updated: {new Date().toLocaleString()}

## Pipeline Health (Last 24 Hours)

```sql pipeline_stats
SELECT
    table_name,
    MAX(updated_at) as last_update,
    COUNT(*) as row_count,
    ROUND(
        EPOCH(CURRENT_TIMESTAMP - MAX(updated_at)) / 3600.0,
        1
    ) as hours_since_update
FROM (
    SELECT 'orders' as table_name, updated_at FROM curated.orders
    UNION ALL
    SELECT 'customers', updated_at FROM curated.customers
    UNION ALL
    SELECT 'products', updated_at FROM curated.products
) t
GROUP BY table_name;
```

<DataTable data={pipeline_stats}>
    <Column id=table_name />
    <Column id=last_update />
    <Column id=row_count fmt='#,##0' />
    <Column id=hours_since_update align=right>
        {#if hours_since_update > 24}
            <span style="color: red;">[!] {hours_since_update}h</span>
        {:else}
            <span style="color: green;">[OK] {hours_since_update}h</span>
        {/if}
    </Column>
</DataTable>

## Data Quality Checks

```sql quality_metrics
SELECT
    'Null customer_ids' as check_name,
    COUNT(*) as failures
FROM curated.orders
WHERE customer_id IS NULL

UNION ALL

SELECT
    'Negative prices',
    COUNT(*) AS failures
FROM curated.products
WHERE price < 0

UNION ALL

SELECT
    'Future order dates',
    COUNT(*) AS failures
FROM curated.orders
WHERE order_date > CURRENT_DATE;
```

<DataTable data={quality_metrics} />

{#if quality_metrics.some(row => row.failures > 0)}
  <Alert status=warning>
    Quality issues detected. Review pipeline.
  </Alert>
{/if}
