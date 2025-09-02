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
    f.reqCurrency,
    CASE 
      WHEN f.reqCurrency = 'THB' THEN 'TH'
      WHEN f.reqCurrency = 'PHP' THEN 'PH'
      WHEN f.reqCurrency = 'BDT' THEN 'BD'
      WHEN f.reqCurrency = 'PKR' THEN 'PK'
      WHEN f.reqCurrency = 'IDR' THEN 'ID'
      ELSE NULL
    END AS country
  FROM `kz-dp-prod.kz_pg_to_bq_realtime.ext_funding_tx` AS f
  CROSS JOIN params p
  WHERE f.type   = 'deposit'
    AND f.status = 'completed'
    -- UTC bounds covering [today-2 00:00 .. today+1 00:00) local
    AND f.completedAt >= TIMESTAMP(DATETIME(DATE_SUB(p.today_date, INTERVAL 2 DAY), TIME '00:00:00'), p.tz)
    AND f.completedAt <  TIMESTAMP(DATETIME(DATE_ADD(p.today_date,  INTERVAL 1 DAY), TIME '00:00:00'), p.tz)
),

-- Cap every of the last 3 days at the SAME clock time (now_time in Bangkok)
capped AS (
  SELECT
    local_date AS date,
    country,
    netAmount
  FROM base, params p
  WHERE local_date BETWEEN DATE_SUB(p.today_date, INTERVAL 2 DAY) AND p.today_date
    AND local_time < p.now_time          -- cap by local time
    AND netAmount IS NOT NULL            -- drop rows without FX
),

-- Aggregate per day
consolidated AS (
  SELECT
    date,
    country,
    AVG(netAmount) AS AverageDeposit,
    SUM(netAmount) AS TotalDeposit
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