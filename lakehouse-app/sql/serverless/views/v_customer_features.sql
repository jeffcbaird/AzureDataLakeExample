-- Business-friendly view: v_customer_features
-- Joins ML feature store with current customer dimension.

CREATE OR ALTER VIEW gold.v_customer_features AS
SELECT
    cf.customer_id,
    dc.last_known_status,
    cf.total_orders,
    cf.total_spend,
    cf.avg_order_value,
    cf.last_order_date,
    cf.distinct_products,
    cf.feature_refreshed_at
FROM gold.customer_features       AS cf
LEFT JOIN gold.v_dim_customer_current AS dc ON cf.customer_id = dc.customer_id;
GO
