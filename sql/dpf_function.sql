-- 3-day sliding window: today, -1d, -2d; each day's data capped at "now" in Asia/Bangkok
WITH params AS (
  SELECT
    'Asia/Bangkok' AS tz,
    CURRENT_DATE('Asia/Bangkok') AS today_date,
    CURRENT_TIME('Asia/Bangkok') AS now_time
),

-- Pull only deposits in the last 3 local days (UTC-pruned)
base AS (
  SELECT
    DATE(DATETIME(f.completedAt, p.tz)) AS local_date,    -- e.g. 2025-08-29
    TIME(DATETIME(f.completedAt, p.tz)) AS local_time,    -- time in Asia/Bangkok
    f.netAmount,
    f.netCurrency,
    f.reqCurrency
  FROM `kz-dp-prod.kz_pg_to_bq_realtime.ext_funding_tx` AS f
  CROSS JOIN params p
  WHERE f.type   = 'deposit'
    AND f.status = 'completed'
    -- UTC bounds covering [today-2 00:00 .. today+1 00:00) local
    AND f.completedAt >= TIMESTAMP(DATETIME(DATE_SUB(p.today_date, INTERVAL 2 DAY), TIME '00:00:00'), p.tz)
    AND f.completedAt <  TIMESTAMP(DATETIME(DATE_ADD(p.today_date,  INTERVAL 1 DAY), TIME '00:00:00'), p.tz)
),

-- Join FX on the SAME LOCAL DATE as the transaction
with_fx AS (
  SELECT
    b.local_date,
    b.local_time,
    b.netAmount,
    b.netCurrency,
    CASE b.netCurrency
      WHEN 'THB' THEN b.netAmount * ex.thb_to_usd
      WHEN 'PHP' THEN b.netAmount * ex.php_to_usd
      WHEN 'BDT' THEN b.netAmount * ex.bdt_to_usd
      WHEN 'PKR' THEN b.netAmount * ex.pkr_to_usd
      WHEN 'IDR' THEN b.netAmount * ex.idr_to_usd
      ELSE NULL
    END AS usdAmount,
       CASE 
      WHEN b.reqCurrency = 'THB' THEN 'TH'
      WHEN b.reqCurrency = 'PHP' THEN 'PH'
      WHEN b.reqCurrency = 'BDT' THEN 'BD'
      WHEN b.reqCurrency = 'PKR' THEN 'PK'
      WHEN b.reqCurrency = 'IDR' THEN 'ID'
      ELSE NULL
    END AS country
  FROM base b
  LEFT JOIN `kz-dp-prod.CURRENCY_prod.currency_exchange_all_pairs` ex
    ON ex.date = b.local_date
),

-- Cap every of the last 3 days at the SAME clock time (now_time in Bangkok)
capped AS (
  SELECT
    local_date AS date,
    country,
    usdAmount
  FROM with_fx, params p
  WHERE local_date BETWEEN DATE_SUB(p.today_date, INTERVAL 2 DAY) AND p.today_date
    AND local_time < p.now_time          -- cap by local time
    AND usdAmount IS NOT NULL            -- drop rows without FX
),

-- Aggregate per day
consolidated AS (
  SELECT
    date,
    country,
    AVG(usdAmount) AS AverageDeposit,
    SUM(usdAmount) AS TotalDeposit
  FROM capped
  GROUP BY date, country
),

today_total AS (
  SELECT country, TotalDeposit AS TotalToday
  FROM consolidated, params p
  WHERE date = p.today_date
)

SELECT
  c.date,
  c.country,
  c.AverageDeposit,
  ROUND(c.TotalDeposit,0) AS TotalDeposit,
  ROUND(c.TotalDeposit / NULLIF(t.TotalToday, 0), 4) AS Weightage
FROM consolidated c 
LEFT JOIN today_total t ON c.country = t.country
WHERE @target_country IS NULL OR c.country = @target_country
ORDER BY c.date DESC;