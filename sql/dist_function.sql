-- Params:
-- @target_date DATE          -- e.g. DATE '2025-09-01' (local "reporting" date)
-- @selected_country STRING    -- e.g. 'TH' (nullable)

WITH deposit_raw AS (
  SELECT
    f.completedAt,
    f.type,
    f.status,
    f.method,
    CAST(f.netAmount AS FLOAT64) AS net_amount,
    f.reqCurrency
  FROM
    `kz-dp-prod.kz_pg_to_bq_realtime.ext_funding_tx` AS f
  WHERE
    f.type = 'deposit'
    AND f.status = 'completed'
    -- Keep only rows whose local (BKK) calendar date == @target_date
    AND DATE(DATETIME(f.completedAt, 'Asia/Bangkok')) = @target_date
  -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
  -- ADDED THIS LINE TO REMOVE DUPLICATES --
  QUALIFY ROW_NUMBER() OVER (PARTITION BY f.id ORDER BY f.updatedAt DESC) = 1
  -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
),
normalized AS (
  SELECT
    CASE
      WHEN reqCurrency = 'THB' THEN 'TH'
      WHEN reqCurrency = 'PHP' THEN 'PH'
      WHEN reqCurrency = 'BDT' THEN 'BD'
      WHEN reqCurrency = 'PKR' THEN 'PK'
      WHEN reqCurrency = 'IDR' THEN 'ID'
      ELSE NULL
    END AS country,
    COALESCE(method, 'UNKNOWN') AS method,
    reqCurrency AS currency,
    net_amount
  FROM
    deposit_raw
  WHERE
    reqCurrency IS NOT NULL
),
grouped AS (
  SELECT
    country,
    method,
    currency,
    COUNT(*) AS deposit_tnx_count,
    SUM(net_amount) AS total_native,
    AVG(net_amount) AS avg_native
  FROM
    normalized
  WHERE
    (@selected_country IS NULL OR country = @selected_country)
  GROUP BY
    country,
    method,
    currency
)
SELECT
  country,
  method,
  currency,
  deposit_tnx_count,
  ROUND(total_native, 0) AS total_deposit_amount_native,
  ROUND(avg_native, 0) AS average_deposit_amount_native,
  CONCAT(
    ROUND(
      SAFE_DIVIDE(
        total_native * 100.0,
        SUM(total_native) OVER (PARTITION BY country)
      ),
      2
    ),
    '%'
  ) AS pct_of_country_total_native
FROM
  grouped
ORDER BY
  country,
  total_deposit_amount_native DESC,
  method;