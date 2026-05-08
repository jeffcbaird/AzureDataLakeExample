-- External table: dim_customer (SCD2)

IF NOT EXISTS (SELECT 1 FROM sys.external_tables WHERE name = 'dim_customer' AND schema_id = SCHEMA_ID('gold'))
BEGIN
    CREATE EXTERNAL TABLE gold.dim_customer (
        customer_id        NVARCHAR(255),
        last_known_status  NVARCHAR(100),
        valid_from         NVARCHAR(50),
        valid_to           NVARCHAR(50),
        is_current         BIT
    )
    WITH (
        LOCATION     = 'gold/dim_customer/**',
        DATA_SOURCE  = gold_adls,
        FILE_FORMAT  = delta_format
    );
END
GO
