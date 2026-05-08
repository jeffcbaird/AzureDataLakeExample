-- External table: customer_features (ML feature store)

IF NOT EXISTS (SELECT 1 FROM sys.external_tables WHERE name = 'customer_features' AND schema_id = SCHEMA_ID('gold'))
BEGIN
    CREATE EXTERNAL TABLE gold.customer_features (
        customer_id          NVARCHAR(255),
        total_orders         BIGINT,
        total_spend          FLOAT,
        avg_order_value      FLOAT,
        last_order_date      DATE,
        distinct_products    BIGINT,
        feature_refreshed_at NVARCHAR(50)
    )
    WITH (
        LOCATION     = 'gold/customer_features/**',
        DATA_SOURCE  = gold_adls,
        FILE_FORMAT  = delta_format
    );
END
GO
