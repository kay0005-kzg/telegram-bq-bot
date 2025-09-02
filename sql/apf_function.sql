-- Declare country param (NULL means "all")
-- DECLARE target_country STRING DEFAULT NULL;  
-- e.g. SET target_country = 'TH';  -- or leave NULL for all

-- 3-day sliding window: today, -1d, -2d, each capped at "now" in Asia/Bangkok
WITH params AS (
  SELECT
    'Asia/Bangkok' AS tz,
    CURRENT_DATE('Asia/Bangkok') AS today_date,
    CURRENT_TIME('Asia/Bangkok') AS now_time
),
windows AS (
  SELECT
    d AS day_offset,
    DATE_SUB(p.today_date, INTERVAL d DAY) AS date,
    TIMESTAMP(DATETIME(DATE_SUB(p.today_date, INTERVAL d DAY), TIME '00:00:00'), p.tz) AS start_ts,
    TIMESTAMP(DATETIME(DATE_SUB(p.today_date, INTERVAL d DAY), p.now_time), p.tz) AS end_ts
  FROM params p, UNNEST(GENERATE_ARRAY(0,2)) AS d
),
map_country AS (
SELECT DISTINCT
    UPPER(a.name) AS brand,
    CASE 
      WHEN f.reqCurrency = 'THB' THEN 'TH'
      WHEN f.reqCurrency = 'PHP' THEN 'PH'
      WHEN f.reqCurrency = 'BDT' THEN 'BD'
      WHEN f.reqCurrency = 'PKR' THEN 'PK'
      WHEN f.reqCurrency = 'IDR' THEN 'ID'
      ELSE NULL
    END AS country,
  FROM `kz-dp-prod.kz_pg_to_bq_realtime.ext_funding_tx` f
  LEFT JOIN `kz-dp-prod.kz_pg_to_bq_realtime.account` a ON f.accountId = a.id
),
-- map_country AS (
--   SELECT
--     UPPER(Brand) AS brand,
--     ANY_VALUE(Country) AS country
--   FROM `kz-dp-prod.MAPPING.brand_whitelabel_country_folderid_mapping`
--   GROUP BY UPPER(Brand)
-- ),

-- Registrations (NAR) within each day's partial window up to "now"
view_total AS (
  SELECT
    w.date,
    CONCAT(a.gamePrefix, m.apiIdentifier) AS username,
    a.gamePrefix,
    a.`group`,
    UPPER(a.name) AS name,
    mc.country,
    m.deposit1At,
    m.deposit2At,
    m.deposit3At,
    DATE(m.registerAt, 'Asia/Bangkok') AS register_asia_date,
    m.id AS member,
    a.id AS account
  FROM `kz-dp-prod.kz_pg_to_bq_realtime.ext_member` AS m
  JOIN `kz-dp-prod.kz_pg_to_bq_realtime.account` AS a
    ON m.accountId = a.id
  LEFT JOIN map_country AS mc
    ON mc.brand = UPPER(a.name)
  -- Assign each row to the correct day-window
  CROSS JOIN windows w
  WHERE m.registerAt >= w.start_ts
    AND m.registerAt <  w.end_ts
),

-- All deposits (for global ranking per user), then we filter by each window later
total_deposit AS (
  SELECT DISTINCT
    CONCAT(a.gamePrefix, m.apiIdentifier) AS username,
    f.memberId,
    f.completedAt,
    UPPER(a.name) AS brand,
    f.reqCurrency,
    f.id,
    f.method,
    CASE 
      WHEN f.reqCurrency = 'THB' THEN 'TH'
      WHEN f.reqCurrency = 'PHP' THEN 'PH'
      WHEN f.reqCurrency = 'BDT' THEN 'BD'
      WHEN f.reqCurrency = 'PKR' THEN 'PK'
      WHEN f.reqCurrency = 'IDR' THEN 'ID'
      ELSE NULL
    END AS country,
    f.createdAt
  FROM `kz-dp-prod.kz_pg_to_bq_realtime.ext_funding_tx` f
  LEFT JOIN `kz-dp-prod.kz_pg_to_bq_realtime.ext_member` m ON f.memberId = m.id
  LEFT JOIN `kz-dp-prod.kz_pg_to_bq_realtime.account` a ON f.accountId = a.id
  WHERE f.type = 'deposit'
    AND f.status = 'completed'
),

-- Rank deposits per user across all time (so FTD/STD/TTD are true 1st/2nd/3rd overall)
ranked_deposit AS (
  SELECT
    td.*,
    RANK() OVER (PARTITION BY username ORDER BY createdAt ASC) AS rank_deposit
  FROM total_deposit td
),

-- For each day-window, keep deposits whose completedAt falls inside that day's partial window
windowed_deposit AS (
  SELECT
    w.date,
    rd.brand,
    rd.country,
    rd.rank_deposit
  FROM ranked_deposit rd
  JOIN windows w
    ON rd.completedAt >= w.start_ts
   AND rd.completedAt <  w.end_ts
),

consolidated_deposit AS (
  SELECT
    date,
    brand,
    country,
    SUM(CASE WHEN rank_deposit = 1 THEN 1 ELSE 0 END) AS FTD,
    SUM(CASE WHEN rank_deposit = 2 THEN 1 ELSE 0 END) AS STD,
    SUM(CASE WHEN rank_deposit = 3 THEN 1 ELSE 0 END) AS TTD
  FROM windowed_deposit
  GROUP BY date, brand, country
),

consolidated_nar AS (
  SELECT
    vt.date,
    vt.name AS brand,
    vt.country,
    COUNT(DISTINCT vt.username) AS NAR
  FROM view_total vt
  GROUP BY vt.date, vt.name, vt.country
)

SELECT
  cn.date,
  cn.brand,
  cn.country,
  cn.NAR,
  COALESCE(cd.FTD, 0) AS FTD,
  COALESCE(cd.STD, 0) AS STD,
  COALESCE(cd.TTD, 0) AS TTD
FROM consolidated_nar cn
LEFT JOIN consolidated_deposit cd
  ON cn.date = cd.date
 AND cn.brand = cd.brand
 AND cn.country = cd.country
WHERE @target_country IS NULL OR cn.country = @target_country
ORDER BY cn.brand, cn.date DESC