-- Gold Delta table CONSTRAINTS
-- Applied idempotently by pipelines/deploy-sql-scripts.yml after each deploy.
-- Run against the Synapse Serverless SQL endpoint (catalog = gold).
--
-- Delta CHECK constraints are stored in the table metadata and enforced on
-- every INSERT / UPDATE / MERGE.  They never reject existing rows on ADD;
-- pre-existing violations will surface on the next write.

-- ── dim_product ───────────────────────────────────────────────────────────────
ALTER TABLE gold.dim_product
    ADD CONSTRAINT dim_product_id_not_null
    CHECK (product_id IS NOT NULL);

ALTER TABLE gold.dim_product
    ADD CONSTRAINT dim_product_sku_not_null
    CHECK (sku IS NOT NULL AND LENGTH(TRIM(sku)) > 0);

ALTER TABLE gold.dim_product
    ADD CONSTRAINT dim_product_unit_cost_non_negative
    CHECK (unit_cost >= 0);

-- ── dim_customer ──────────────────────────────────────────────────────────────
ALTER TABLE gold.dim_customer
    ADD CONSTRAINT dim_customer_id_not_null
    CHECK (customer_id IS NOT NULL);

ALTER TABLE gold.dim_customer
    ADD CONSTRAINT dim_customer_valid_to_after_from
    CHECK (valid_to >= valid_from);

-- ── fact_orders ───────────────────────────────────────────────────────────────
ALTER TABLE gold.fact_orders
    ADD CONSTRAINT fact_orders_order_id_not_null
    CHECK (order_id IS NOT NULL);

ALTER TABLE gold.fact_orders
    ADD CONSTRAINT fact_orders_amount_non_negative
    CHECK (amount >= 0);

ALTER TABLE gold.fact_orders
    ADD CONSTRAINT fact_orders_quantity_positive
    CHECK (quantity >= 1);

ALTER TABLE gold.fact_orders
    ADD CONSTRAINT fact_orders_order_date_not_null
    CHECK (order_date IS NOT NULL);

-- ── daily_revenue_summary ─────────────────────────────────────────────────────
ALTER TABLE gold.daily_revenue_summary
    ADD CONSTRAINT daily_revenue_total_non_negative
    CHECK (total_revenue >= 0);

ALTER TABLE gold.daily_revenue_summary
    ADD CONSTRAINT daily_revenue_order_count_positive
    CHECK (order_count >= 0);

-- ── customer_features ─────────────────────────────────────────────────────────
ALTER TABLE gold.customer_features
    ADD CONSTRAINT customer_features_id_not_null
    CHECK (customer_id IS NOT NULL);

ALTER TABLE gold.customer_features
    ADD CONSTRAINT customer_features_total_orders_non_negative
    CHECK (total_orders >= 0);
