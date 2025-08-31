-- Params:
-- @cutoff_local_dt DATETIME   -- e.g. 2025-08-21 12:00:00 (Asia/Ho_Chi_Minh)
-- @selected_country STRING     -- e.g. 'TH' (nullable)

WITH deposit_transaction_raw AS (
  SELECT
    createdAt,
    reqCurrency,
    method,
    netAmount
  FROM `kz-dp-prod.kz_pg_to_bq_realtime.ext_funding_tx`
  WHERE type = 'deposit'
    AND createdAt <= TIMESTAMP(@cutoff_local_dt, "Asia/Ho_Chi_Minh")
),
fx_rates AS (
  SELECT
    date,
    bdt_to_usd,
    idr_to_usd,
    php_to_usd,
    pkr_to_usd,
    thb_to_usd
  FROM `kz-dp-prod.CURRENCY_prod.currency_exchange_all_pairs`
  WHERE date = CURRENT_DATE()
  LIMIT 1
),
deposit_summary AS (
  SELECT
    CASE
      WHEN reqCurrency = 'THB' THEN 'TH'
      WHEN reqCurrency = 'PHP' THEN 'PH'
      WHEN reqCurrency = 'BDT' THEN 'BD'
      WHEN reqCurrency = 'PKR' THEN 'PK'
      WHEN reqCurrency = 'IDR' THEN 'ID'
      ELSE NULL
    END AS country,
    method,
    CAST(netAmount AS FLOAT64) AS deposit_amount,
    reqCurrency
  FROM deposit_transaction_raw
),
grouped AS (
  SELECT
    ds.country,
    COALESCE(ds.method, 'UNKNOWN') AS method,
    COUNT(*) AS deposit_tnx_count,
    SUM(
      CASE ds.reqCurrency
        WHEN 'THB' THEN ds.deposit_amount * fx.thb_to_usd
        WHEN 'PHP' THEN ds.deposit_amount * fx.php_to_usd
        WHEN 'BDT' THEN ds.deposit_amount * fx.bdt_to_usd
        WHEN 'PKR' THEN ds.deposit_amount * fx.pkr_to_usd
        WHEN 'IDR' THEN ds.deposit_amount * fx.idr_to_usd
        ELSE NULL
      END
    ) AS total_usd,
    AVG(
      CASE ds.reqCurrency
        WHEN 'THB' THEN ds.deposit_amount * fx.thb_to_usd
        WHEN 'PHP' THEN ds.deposit_amount * fx.php_to_usd
        WHEN 'BDT' THEN ds.deposit_amount * fx.bdt_to_usd
        WHEN 'PKR' THEN ds.deposit_amount * fx.pkr_to_usd
        WHEN 'IDR' THEN ds.deposit_amount * fx.idr_to_usd
        ELSE NULL
      END
    ) AS avg_usd
  FROM deposit_summary ds
  CROSS JOIN fx_rates fx
  WHERE (@selected_country IS NULL OR ds.country = @selected_country)
  GROUP BY ds.country, method
)
SELECT
  country,
  method,
  deposit_tnx_count,
  ROUND(total_usd, 0)   AS total_deposit_amount_usd,
  ROUND(avg_usd, 0)     AS average_deposit_amount_usd,
  CONCAT(
    ROUND(
      SAFE_DIVIDE(
        total_usd * 100.0,
        SUM(total_usd) OVER (PARTITION BY country)
      ),
      2
    ),
    '%'
  ) AS pct_of_country_total_usd
FROM grouped
ORDER BY country, total_usd DESC, method;
