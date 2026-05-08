-- Business-friendly view: v_daily_revenue_summary

CREATE OR ALTER VIEW gold.v_daily_revenue_summary AS
SELECT
    order_date,
    total_revenue,
    order_count,
    avg_order_value,
    distinct_customers,
    -- Running 7-day average for trend sparklines in Power BI.
    AVG(total_revenue) OVER (
        ORDER BY order_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS revenue_7d_avg
FROM gold.daily_revenue_summary;
GO
