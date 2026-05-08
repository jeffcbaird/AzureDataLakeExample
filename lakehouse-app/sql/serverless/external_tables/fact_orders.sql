-- External table: fact_orders

IF NOT EXISTS (SELECT 1 FROM sys.external_tables WHERE name = 'fact_orders' AND schema_id = SCHEMA_ID('gold'))
BEGIN
    CREATE EXTERNAL TABLE gold.fact_orders (
        order_id    NVARCHAR(255),
        customer_id NVARCHAR(255),
        product_id  NVARCHAR(255),
        quantity    BIGINT,
        unit_price  FLOAT,
        amount      FLOAT,
        status      NVARCHAR(100),
        order_date  DATE,
        _date       NVARCHAR(10)
    )
    WITH (
        LOCATION     = 'gold/fact_orders/**',
        DATA_SOURCE  = gold_adls,
        FILE_FORMAT  = delta_format
    );
END
GO
