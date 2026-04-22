-- ============================================================
-- FEATURE ENGINEERING V2 - Corrige selon les regles de l'entreprise
-- ============================================================
-- Sortants (MO) = mSOriginating UNIQUEMENT
-- Entrants (MT) = mSTerminating UNIQUEMENT
-- callForwarding = PAS inclus (ni MO ni MT)
-- SMS ignores
--
-- Execution estimee : 2-3 heures sur 741M lignes
-- ============================================================

DROP TYPE IF EXISTS features_msisdn_v2 CASCADE;
DROP TABLE IF EXISTS features_msisdn_v2 CASCADE;

CREATE TABLE features_msisdn_v2 AS
SELECT
    msisdn,

    -- =============================================
    -- 1. NOMBRE D'APPELS
    -- =============================================
    COUNT(*) FILTER (WHERE call_type = 'mSOriginating')
        AS appels_sortants,

    COUNT(*) FILTER (WHERE call_type = 'mSTerminating')
        AS appels_entrants,


    -- =============================================
    -- 2. DUREE TOTALE
    -- =============================================
    COALESCE(SUM(duration_seconds) FILTER (WHERE call_type = 'mSOriginating'), 0)
        AS duree_sortants,

    COALESCE(SUM(duration_seconds) FILTER (WHERE call_type = 'mSTerminating'), 0)
        AS duree_entrants,

    -- =============================================
    -- 3. DUREE MOYENNE
    -- =============================================
    ROUND(AVG(duration_seconds) FILTER (WHERE call_type = 'mSOriginating')::numeric, 2)
        AS avg_duree_sortants,

    ROUND(AVG(duration_seconds) FILTER (WHERE call_type = 'mSTerminating')::numeric, 2)
        AS avg_duree_entrants,

    -- =============================================
    -- 4. VARIANCE SORTANTS (en %)
    -- =============================================
    ROUND(
        COUNT(DISTINCT called_number) FILTER (WHERE call_type = 'mSOriginating')::numeric
        / NULLIF(COUNT(*) FILTER (WHERE call_type = 'mSOriginating'), 0)::numeric * 100, 2
    ) AS variance_sortants,

    -- =============================================
    -- 5. VARIANCE ENTRANTS (en %)
    -- =============================================
    ROUND(
        COUNT(DISTINCT calling_number) FILTER (WHERE call_type = 'mSTerminating')::numeric
        / NULLIF(COUNT(*) FILTER (WHERE call_type = 'mSTerminating'), 0)::numeric * 100, 2
    ) AS variance_entrants,

    -- =============================================
    -- 6. MOBILITE (lac + cell_id combines)
    -- =============================================
    COUNT(DISTINCT lac || '-' || cell_id) FILTER (WHERE call_type = 'mSOriginating')
        AS location_count_sortants,

    COUNT(DISTINCT lac || '-' || cell_id) FILTER (WHERE call_type = 'mSTerminating')
        AS location_count_entrants,

    COUNT(DISTINCT lac || '-' || cell_id)
        AS location_count,

    -- =============================================
    -- 7. ACTIVE HOURS
    -- =============================================
    COUNT(DISTINCT DATE_TRUNC('hour', timestamp)) FILTER (WHERE call_type = 'mSOriginating')
        AS active_hours,

    -- =============================================
    -- 8. DISTINCT IMEI
    -- =============================================
    COUNT(DISTINCT imei)
        AS distinct_imei,

    -- =============================================
    -- 9. UNIQUE CALLED / CALLING
    -- =============================================
    COUNT(DISTINCT called_number) FILTER (WHERE call_type = 'mSOriginating')
        AS unique_called,

    COUNT(DISTINCT calling_number) FILTER (WHERE call_type = 'mSTerminating')
        AS unique_calling,

    -- =============================================
    -- 10. JOURS ACTIFS
    -- =============================================
    COUNT(DISTINCT DATE(timestamp))
        AS nb_jours_actifs

FROM cdr_data
GROUP BY msisdn;

CREATE INDEX idx_fv2_msisdn ON features_msisdn_v2(msisdn);
CREATE INDEX idx_fv2_calls ON features_msisdn_v2(appels_sortants DESC);
