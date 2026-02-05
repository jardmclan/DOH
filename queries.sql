-- name: load_main_data
WITH dx AS (
  SELECT DISTINCT record_id, TRIM(diagnosis) AS substance
  FROM discharge_data_view_diag_su
  WHERE diagnosis IS NOT NULL AND TRIM(diagnosis) <> ''
)
SELECT
  dx.record_id,
  dx.substance,
  m.county, m.city, m.zip, m.hawaii_residency,
  m.age_group, m.sex, m.year
FROM dx
JOIN discharge_data_view_demographics m ON m.record_id = dx.record_id;

-- name: load_filtered_data


-- name: load_polysubstance_data
WITH
dx_union AS (
  SELECT DISTINCT record_id, TRIM(diagnosis) AS substance
  FROM discharge_data_view_diag_su
  WHERE diagnosis IS NOT NULL AND TRIM(diagnosis) <> ''
),
poly_ids AS (
  -- polysubstance = ≥2 distinct substances
  SELECT record_id
  FROM dx_union
  GROUP BY record_id
  HAVING COUNT(DISTINCT substance) >= 2
)
SELECT
  u.record_id,
  u.substance,
  m.county, m.city, m.zip, m.hawaii_residency,
  m.age_group, m.sex,
  CAST(m.year AS INTEGER) AS year
FROM dx_union AS u
JOIN poly_ids AS p
  ON p.record_id = u.record_id
JOIN discharge_data_view_demographics AS m
  ON m.record_id = u.record_id
WHERE
  CAST(m.year AS INTEGER) BETWEEN 2018 AND 2024
  AND LOWER(COALESCE(NULLIF(TRIM(m.age_group), ''), 'unknown')) <> 'unknown';  -- drop Unknown/blank ages




-- name: load_sud_primary_mh_secondary_v2
WITH
sud_union AS (
  SELECT DISTINCT record_id, TRIM(diagnosis) AS sud_substance, '' AS sud_pos
  FROM discharge_data_view_diag_su
  WHERE diagnosis IS NOT NULL AND TRIM(diagnosis) <> ''
),
mh_union AS (
  SELECT record_id, TRIM(diagnosis) AS mh_dx, '' AS mh_pos
  FROM discharge_data_view_diag_mh
  WHERE diagnosis IS NOT NULL AND TRIM(diagnosis) <> ''
),
co AS (
  SELECT s.record_id, s.sud_substance, m.mh_dx
  FROM sud_union s
  JOIN mh_union m ON m.record_id = s.record_id
)
SELECT
  co.record_id,
  co.sud_substance                    AS su_diagnosis,
  co.mh_dx                            AS mh_diagnosis,
  d.county, d.city, d.zip, d.hawaii_residency,
  d.age_group, d.sex,
  CAST(d.year AS INTEGER)    AS year
FROM co
JOIN discharge_data_view_demographics d ON d.record_id = co.record_id
WHERE CAST(d.year AS INTEGER) BETWEEN 2018 AND 2024
  AND LOWER(COALESCE(NULLIF(TRIM(d.age_group), ''), 'unknown')) <> 'unknown';
