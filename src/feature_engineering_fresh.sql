-- ============================================================
-- FEATURE ENGINEERING - DONNEES FRESH (test independant)
-- ============================================================
-- Identique a feature_engineering_v2.sql, mais :
--   source  = cdr_data_fresh   (les 6 Go de donnees neuves)
--   sortie  = features_msisdn_fresh
-- Aucune table d'entrainement n'est touchee.
-- ============================================================

SET work_mem = '64MB';
SET max_parallel_workers_per_gather = 0;

DROP TABLE IF EXISTS features_msisdn_fresh CASCADE;

CREATE TABLE features_msisdn_fresh AS
SELECT
    msisdn,

    -- 1. NOMBRE D'APPELS
    COUNT(*) FILTER (WHERE call_type = 'mSOriginating')
        AS appels_sortants,
    COUNT(*) FILTER (WHERE call_type = 'mSTerminating')
        AS appels_entrants,

    -- 2. DUREE TOTALE
    COALESCE(SUM(duration_seconds) FILTER (WHERE call_type = 'mSOriginating'), 0)
        AS duree_sortants,
    COALESCE(SUM(duration_seconds) FILTER (WHERE call_type = 'mSTerminating'), 0)
        AS duree_entrants,

    -- 3. DUREE MOYENNE
    ROUND(AVG(duration_seconds) FILTER (WHERE call_type = 'mSOriginating')::numeric, 2)
        AS avg_duree_sortants,
    ROUND(AVG(duration_seconds) FILTER (WHERE call_type = 'mSTerminating')::numeric, 2)
        AS avg_duree_entrants,

    -- 4. VARIANCE SORTANTS (en %)
    ROUND(
        COUNT(DISTINCT called_number) FILTER (WHERE call_type = 'mSOriginating')::numeric
        / NULLIF(COUNT(*) FILTER (WHERE call_type = 'mSOriginating'), 0)::numeric * 100, 2
    ) AS variance_sortants,

    -- 5. VARIANCE ENTRANTS (en %)
    ROUND(
        COUNT(DISTINCT calling_number) FILTER (WHERE call_type = 'mSTerminating')::numeric
        / NULLIF(COUNT(*) FILTER (WHERE call_type = 'mSTerminating'), 0)::numeric * 100, 2
    ) AS variance_entrants,

    -- 6. MOBILITE (lac + cell_id combines)
    COUNT(DISTINCT lac || '-' || cell_id) FILTER (WHERE call_type = 'mSOriginating')
        AS location_count_sortants,
    COUNT(DISTINCT lac || '-' || cell_id) FILTER (WHERE call_type = 'mSTerminating')
        AS location_count_entrants,
    COUNT(DISTINCT lac || '-' || cell_id)
        AS location_count,

    -- 7. ACTIVE HOURS
    COUNT(DISTINCT DATE_TRUNC('hour', timestamp)) FILTER (WHERE call_type = 'mSOriginating')
        AS active_hours,

    -- 8. DISTINCT IMEI
    COUNT(DISTINCT imei)
        AS distinct_imei,

    -- 9. UNIQUE CALLED / CALLING
    COUNT(DISTINCT called_number) FILTER (WHERE call_type = 'mSOriginating')
        AS unique_called,
    COUNT(DISTINCT calling_number) FILTER (WHERE call_type = 'mSTerminating')
        AS unique_calling,

    -- 10. JOURS ACTIFS
    COUNT(DISTINCT DATE(timestamp))
        AS nb_jours_actifs

FROM cdr_data_fresh
GROUP BY msisdn;

CREATE INDEX idx_ffresh_msisdn ON features_msisdn_fresh(msisdn);
