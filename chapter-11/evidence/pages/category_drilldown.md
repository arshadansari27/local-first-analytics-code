# Category Analysis

<Dropdown
    name=category
    title="Select Category"
>
    <DropdownOption value="Electronics" />
    <DropdownOption value="Clothing" />
    <DropdownOption value="Home & Garden" />
</Dropdown>

```sql category_sales
SELECT
    DATE_TRUNC('week', order_date) as week,
    SUM(total_amount) as revenue
FROM curated.order_items
WHERE category = '${inputs.category}'
  AND order_date >= CURRENT_DATE - INTERVAL 90 DAY
GROUP BY 1
ORDER BY 1;
```

<LineChart data={category_sales} x=week y=revenue />
