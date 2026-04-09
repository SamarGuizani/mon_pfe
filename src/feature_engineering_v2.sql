-- ============================================================
-- FEATURE ENGINEERING V2 - Corrige selon les regles de l'entreprise
-- ============================================================
-- Sortants (MO) = mSOriginating
-- Entrants (MT) = mSTerminating
-- callForwarding = compte comme sortant
-- SMS ignores (mSOriginatingSMSinMSC, mSTerminatingSMSinMSC)
--
-- Corrections appliquees :
--   - location = lac||'-'||cell_id (pas cell_id seul)
--   - variance en % (pas en ratio 0-1)
--   - active_hours ajoute (DISTINCT DATE_TRUNC('hour'))
--   - distinct_imei ajoute (>= 3 = SIM Box)
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
    -- Total appels (hors SMS)
    COUNT(*) FILTER (WHERE call_type IN ('mSOriginating', 'mSTerminating', 'callForwarding'))
        AS nombre_appels,

    -- Appels sortants (MO) - Rule: count(*) filter (where type_call='MO')
    COUNT(*) FILTER (WHERE call_type IN ('mSOriginating', 'callForwarding'))
        AS appels_sortants,

    -- Appels entrants (MT) - Rule: COUNT(callingnumber)
    COUNT(*) FILTER (WHERE call_type = 'mSTerminating')
        AS appels_entrants,

    -- =============================================
    -- 2. DUREE TOTALE
    -- =============================================
    -- Duree totale sortants - Rule: SUM(callduration) FILTER (WHERE type_call='MO')
    COALESCE(SUM(duration_seconds) FILTER (WHERE call_type IN ('mSOriginating', 'callForwarding')), 0)
        AS duree_sortants,

    -- Duree totale entrants - Rule: SUM(callduration) FILTER (WHERE type_call='MT')
    -- Regle bypass general : coalesce(SUM(callduration) FILTER (WHERE type_call='MT'),0) = 0 → suspect si MT duration = 0
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
    -- 4. VARIANCE SORTANTS (en %)
    --    = (distinct appeles / total appels sortants) * 100
    --    Regles entreprise : seuil >= 85%, 90%, 95%, ou 100%
    --    Proche de 100% = chaque appel vers un numero DIFFERENT (tres suspect)
    --    Proche de 0%   = appelle toujours le MEME numero (normal)
    -- =============================================
    ROUND(
        COUNT(DISTINCT called_number) FILTER (WHERE call_type IN ('mSOriginating', 'callForwarding'))::FLOAT
        / NULLIF(COUNT(*) FILTER (WHERE call_type IN ('mSOriginating', 'callForwarding')), 0)::FLOAT * 100, 2
    ) AS variance_sortants,

    -- =============================================
    -- 5. VARIANCE ENTRANTS (en %)
    --    = (distinct appelants / total appels entrants) * 100
    -- =============================================
    ROUND(
        COUNT(DISTINCT calling_number) FILTER (WHERE call_type = 'mSTerminating')::FLOAT
        / NULLIF(COUNT(*) FILTER (WHERE call_type = 'mSTerminating'), 0)::FLOAT * 100, 2
    ) AS variance_entrants,

    -- =============================================
    -- 6. MOBILITE
    --    Regle entreprise : COUNT(DISTINCT lac||'-'||cell_id)
    --    PAS cell_id seul ! Il faut combiner lac + cell_id
    --    SIM Box = tres peu de locations (fixe, <= 2-3)
    --    Humain  = beaucoup de locations (bouge)
    -- =============================================
    -- Locations distinctes globales (lac+cell combinee)
    COUNT(DISTINCT lac || '-' || cell_id)
        AS location_count,

    -- Locations distinctes sortants
    COUNT(DISTINCT lac || '-' || cell_id) FILTER (WHERE call_type IN ('mSOriginating', 'callForwarding'))
        AS location_count_sortants,

    -- Locations distinctes entrants
    COUNT(DISTINCT lac || '-' || cell_id) FILTER (WHERE call_type = 'mSTerminating')
        AS location_count_entrants,

    -- =============================================
    -- 7. ACTIVE HOURS (ajoute - manquait avant)
    --    Regle entreprise : COUNT(DISTINCT DATE_TRUNC('hour', timestamp)) <= 3
    --    SIM Box = active seulement quelques heures (burst)
    --    Humain  = active sur beaucoup d'heures differentes
    -- =============================================
    COUNT(DISTINCT DATE_TRUNC('hour', timestamp))
        AS active_hours,

    -- =============================================
    -- 8. DISTINCT IMEI (ajoute - manquait avant)
    --    Regle entreprise : COUNT(DISTINCT imei) >= 3 = SIM Box
    --    SIM Box = un msisdn utilise dans plusieurs appareils
    --    Humain  = 1 seul IMEI (son telephone)
    -- =============================================
    COUNT(DISTINCT imei)
        AS distinct_imei,

    -- =============================================
    -- 9. UNIQUE CALLED / CALLING (details)
    --    Pour analyse detaillee
    -- =============================================
    COUNT(DISTINCT called_number) FILTER (WHERE call_type IN ('mSOriginating', 'callForwarding'))
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

-- Index pour accelerer les requetes
CREATE INDEX idx_fv2_msisdn ON features_msisdn_v2(msisdn);
CREATE INDEX idx_fv2_calls ON features_msisdn_v2(appels_sortants DESC);
