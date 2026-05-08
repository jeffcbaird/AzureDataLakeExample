-- External table: daily_revenue_summary

IF NOT EXISTS (SELECT 1 FROM sys.external_tables WHERE name = 'daily_revenue_summary' AND schema_id = SCHEMA_ID('gold'))
BEGIN
    CREATE EXTERNAL TABLE gold.daily_revenue_summary (
        order_date          DATE,
        total_revenue       FLOAT,
        order_count         BIGINT,
        avg_order_value     FLOAT,
        distinct_customers  BIGINT,
        _date               NVARCHAR(10)
    )
    WITH (
        LOCATION     = 'gold/daily_revenue_summary/**',
        DATA_SOURCE  = gold_adls,
        FILE_FORMAT  = delta_format
    );
END
GO
