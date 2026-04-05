-- ============================================================
-- FEATURE ENGINEERING V2 : Features personnalisees par Samar
-- ============================================================
-- Sortants = mSOriginating, callForwarding
-- Entrants = mSTerminating
-- On ignore les SMS (mSOriginatingSMSinMSC, mSTerminatingSMSinMSC)
--
-- Execution estimee : 2-3 heures sur 741M lignes
-- ============================================================

DROP TABLE IF EXISTS features_msisdn_v2;

CREATE TABLE features_msisdn_v2 AS
SELECT
    msisdn,

    -- =============================================
    -- 1. NOMBRE D'APPELS
    -- =============================================
    -- Total (hors SMS)
    COUNT(*) FILTER (WHERE call_type IN ('mSOriginating', 'mSTerminating', 'callForwarding'))
        AS nombre_appels,

    -- Appels sortants
    COUNT(*) FILTER (WHERE call_type IN ('mSOriginating', 'callForwarding'))
        AS appels_sortants,

    -- Appels entrants
    COUNT(*) FILTER (WHERE call_type = 'mSTerminating')
        AS appels_entrants,

    -- =============================================
    -- 2. DUREE TOTALE
    -- =============================================
    -- Duree totale (tous appels)
    COALESCE(SUM(duration_seconds) FILTER (WHERE call_type IN ('mSOriginating', 'mSTerminating', 'callForwarding')), 0)
        AS duree_totale,

    -- Duree sortants
    COALESCE(SUM(duration_seconds) FILTER (WHERE call_type IN ('mSOriginating', 'callForwarding')), 0)
        AS duree_sortants,

    -- Duree entrants
    COALESCE(SUM(duration_seconds) FILTER (WHERE call_type = 'mSTerminating'), 0)
        AS duree_entrants,

    -- =============================================
    -- 3. DUREE MOYENNE
    -- =============================================
    -- AVG duree sortants
    ROUND(AVG(duration_seconds) FILTER (WHERE call_type IN ('mSOriginating', 'callForwarding'))::numeric, 2)
        AS avg_duree_sortants,

    -- AVG duree entrants
    ROUND(AVG(duration_seconds) FILTER (WHERE call_type = 'mSTerminating')::numeric, 2)
        AS avg_duree_entrants,

    -- =============================================
    -- 4. VARIANCE SORTANTS
    --    = distinct appeles / total appels sortants
    --    Proche de 1.0 = chaque appel vers un numero different (suspect)
    --    Proche de 0.0 = appelle toujours le meme numero (normal)
    -- =============================================
    ROUND(
        COUNT(DISTINCT called_number) FILTER (WHERE call_type IN ('mSOriginating', 'callForwarding'))::numeric
        / NULLIF(COUNT(*) FILTER (WHERE call_type IN ('mSOriginating', 'callForwarding')), 0), 4
    ) AS variance_sortants,

    -- =============================================
    -- 5. VARIANCE ENTRANTS
    --    = distinct appelants / total appels entrants
    --    Proche de 1.0 = recoit des appels de plein de numeros differents
    --    Proche de 0.0 = recoit toujours du meme numero
    -- =============================================
    ROUND(
        COUNT(DISTINCT calling_number) FILTER (WHERE call_type = 'mSTerminating')::numeric
        / NULLIF(COUNT(*) FILTER (WHERE call_type = 'mSTerminating'), 0), 4
    ) AS variance_entrants,

    -- =============================================
    -- 6. MOBILITE
    --    Distinct locations (cell_id) pour sortants et entrants
    --    SIM Box = tres peu de locations (fixe)
    --    Humain normal = beaucoup de locations (bouge)
    -- =============================================
    -- Locations distinctes globales
    COUNT(DISTINCT cell_id)
        AS distinct_locations,

    -- Locations distinctes sortants
    COUNT(DISTINCT cell_id) FILTER (WHERE call_type IN ('mSOriginating', 'callForwarding'))
        AS distinct_locations_sortants,

    -- Locations distinctes entrants
    COUNT(DISTINCT cell_id) FILTER (WHERE call_type = 'mSTerminating')
        AS distinct_locations_entrants

FROM cdr_data
GROUP BY msisdn;

-- Index
CREATE INDEX idx_features_v2_msisdn ON features_msisdn_v2(msisdn);
CREATE INDEX idx_features_v2_appels ON features_msisdn_v2(nombre_appels DESC);
