-- Business-friendly view: v_fact_orders
-- Power BI connects here, never directly to the external table.
-- Joins fact with current dimension rows to produce a denormalised view.

CREATE OR ALTER VIEW gold.v_fact_orders AS
SELECT
    f.order_id,
    f.customer_id,
    f.product_id,
    p.sku                AS product_sku,
    p.name               AS product_name,
    p.category           AS product_category,
    f.quantity,
    f.unit_price,
    f.amount,
    f.status,
    f.order_date,
    f._date
FROM gold.fact_orders          AS f
LEFT JOIN gold.dim_product     AS p ON f.product_id = p.product_id
WHERE f.order_date IS NOT NULL;
GO
