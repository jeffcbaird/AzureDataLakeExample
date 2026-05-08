-- External table: dim_product
-- Points at the Gold Delta path in ADLS Gen2.
-- Power BI connects to views in sql/serverless/views/, never directly here.

IF NOT EXISTS (SELECT 1 FROM sys.external_tables WHERE name = 'dim_product' AND schema_id = SCHEMA_ID('gold'))
BEGIN
    CREATE EXTERNAL TABLE gold.dim_product (
        product_id   NVARCHAR(255),
        sku          NVARCHAR(255),
        name         NVARCHAR(512),
        category     NVARCHAR(255),
        unit_cost    FLOAT
    )
    WITH (
        LOCATION     = 'gold/dim_product/**',
        DATA_SOURCE  = gold_adls,
        FILE_FORMAT  = delta_format
    );
END
GO
