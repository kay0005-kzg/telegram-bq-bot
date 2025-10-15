-- pmh_function.sql (Updated)

-- Optimized Query
WITH all_transactions AS (
  -- STEP 1: Scan the base table
  SELECT
    f.type,
    CASE
      WHEN f.reqCurrency = 'THB' THEN 'TH'
      WHEN f.reqCurrency = 'PHP' THEN 'PH'
      WHEN f.reqCurrency = 'BDT' THEN 'BD'
      WHEN f.reqCurrency = 'PKR' THEN 'PK'
      WHEN f.reqCurrency = 'IDR' THEN 'ID'
      ELSE NULL
    END AS country,
    f.createdAt,
    f.completedAt,
    f.providerKey,
    f.method,
    a.name AS brand_name, -- Keep brand_name for the join
    f.status,
    f.netAmount
  FROM
    `kz-dp-prod.kz_pg_to_bq_realtime.ext_funding_tx` AS f
  LEFT JOIN
    `kz-dp-prod.kz_pg_to_bq_realtime.account` AS a ON f.accountId = a.id
  WHERE
    f.type IN ('deposit', 'withdraw')
    AND f.status IN ('completed', 'error' ,'timeout')
    AND DATE(DATETIME(COALESCE(f.completedAt, f.createdAt), 'Asia/Bangkok')) = @target_date
    AND (@selected_country IS NULL OR 
         (CASE 
            WHEN f.reqCurrency = 'THB' THEN 'TH'
            WHEN f.reqCurrency = 'PHP' THEN 'PH'
            WHEN f.reqCurrency = 'BDT' THEN 'BD'
            WHEN f.reqCurrency = 'PKR' THEN 'PK'
            WHEN f.reqCurrency = 'IDR' THEN 'ID'
            ELSE NULL 
          END) = @selected_country)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY f.id ORDER BY f.updatedAt DESC) = 1
)
-- STEP 2: Perform aggregation
SELECT
  CASE 
    WHEN t.type = 'deposit' THEN 'DEPOSIT' 
    WHEN t.type = 'withdraw' THEN 'WITHDRAWAL' 
  END AS tnx_type,
  t.providerKey,
  t.method,
  t.brand_name as brand, -- Output brand_name
  t.status,
  t.country,
  AVG(TIMESTAMP_DIFF(t.completedAt, t.createdAt, SECOND)) AS avg_diff_seconds_transaction,
  COUNT(*) AS total_count,
  COUNTIF(TIMESTAMP_DIFF(t.completedAt, t.createdAt, SECOND) < 180) AS transaction_within_180s,
  COUNTIF(TIMESTAMP_DIFF(t.completedAt, t.createdAt, SECOND) < 300) AS transaction_within_300s,
  COUNTIF(TIMESTAMP_DIFF(t.completedAt, t.createdAt, SECOND) < 900) AS transaction_within_900s
FROM
  all_transactions AS t
GROUP BY
  tnx_type,
  providerKey,
  method,
  brand_name, -- Group by brand_name
  status,
  country;