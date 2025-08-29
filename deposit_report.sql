WITH deposit_transaction_raw AS (
  SELECT
    *
  FROM `kz-dp-prod.kz_pg_to_bq_realtime.ext_funding_tx`
  WHERE type = 'deposit'
    AND DATETIME(TIMESTAMP(createdAt), "Asia/Ho_Chi_Minh") <= DATETIME(@cutoff_ts, "Asia/Ho_Chi_Minh")
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
    createdAt as created_time,
    netAmount AS deposit_amount
  FROM deposit_transaction_raw
  WHERE (
      @selected_country IS NULL
      OR CASE
          WHEN reqCurrency = 'THB' THEN 'TH'
          WHEN reqCurrency = 'PHP' THEN 'PH'
          WHEN reqCurrency = 'BDT' THEN 'BD'
          WHEN reqCurrency = 'PKR' THEN 'PK'
          WHEN reqCurrency = 'IDR' THEN 'ID'
          ELSE NULL
        END = @selected_country
  )
)
SELECT
  country,
  method,
  COUNT(*) AS deposit_tnx_count,
  ROUND(SUM(deposit_amount),0) AS total_deposit_amount,
  ROUND(AVG(deposit_amount),0) AS average_deposit_amount,
  CONCAT(
    ROUND(SUM(deposit_amount) * 100.0 / SUM(SUM(deposit_amount)) OVER (PARTITION BY country),2),
    '%'
  ) AS pct_of_country_total
FROM deposit_summary
GROUP BY country, method
ORDER BY country, method;
