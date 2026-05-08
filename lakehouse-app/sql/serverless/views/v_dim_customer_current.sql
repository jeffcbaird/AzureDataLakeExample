-- Business-friendly view: v_dim_customer_current
-- Exposes only the active SCD2 row for each customer.

CREATE OR ALTER VIEW gold.v_dim_customer_current AS
SELECT
    customer_id,
    last_known_status,
    valid_from
FROM gold.dim_customer
WHERE is_current = 1;
GO
