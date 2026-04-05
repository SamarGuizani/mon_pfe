-- ============================================================
-- FEATURE ENGINEERING : Extraction des 12 features par MSISDN
-- ============================================================
-- Cette requete scanne les 741M lignes UNE SEULE FOIS
-- et cree une petite table "features_msisdn" avec 1 ligne par numero
-- C'est cette table que Python utilisera pour le Machine Learning
--
-- Execution estimee : 1-2 heures sur 83 Go
-- Resultat : quelques millions de lignes max (une par msisdn unique)
-- ============================================================

DROP TABLE IF EXISTS features_msisdn;

CREATE TABLE features_msisdn AS
SELECT
    msisdn,

    -- === FEATURES DE VOLUME ===
    -- 1. Nombre total d'appels
    COUNT(*) AS nombre_appels,

    -- 2. Duree totale en secondes
    COALESCE(SUM(duration_seconds), 0) AS duree_totale_sec,

    -- 3. Duree moyenne d'un appel
    ROUND(AVG(duration_seconds)::numeric, 2) AS duree_moyenne,

    -- 4. Ratio d'appels courts (<30s) : les robots font des appels tres courts
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE duration_seconds IS NOT NULL AND duration_seconds < 30)
        / NULLIF(COUNT(*), 0), 2
    ) AS ratio_appels_courts,

    -- 5. Nombre de destinataires uniques
    COUNT(DISTINCT called_number) AS nb_destinataires_uniques,

    -- === FEATURES EQUIPEMENT (IMEI) ===
    -- 6. Nombre d'IMEI utilises : SIM Box = plusieurs SIM dans peu d'appareils
    COUNT(DISTINCT imei) AS nb_imei_utilises,

    -- === FEATURES GEOGRAPHIQUES ===
    -- 7. Nombre de cellules uniques : SIM Box = fixe (peu de cellules)
    COUNT(DISTINCT cell_id) AS nb_cellules_uniques,

    -- 8. Nombre de LAC uniques : mobilite geographique
    COUNT(DISTINCT lac) AS nb_lac_uniques,

    -- === FEATURES TEMPORELLES ===
    -- 9. Nombre de jours d'activite
    COUNT(DISTINCT DATE(timestamp)) AS nb_jours_actifs,

    -- 10. Appels par jour (intensite)
    ROUND(
        COUNT(*)::numeric / NULLIF(COUNT(DISTINCT DATE(timestamp)), 0), 2
    ) AS appels_par_jour,

    -- 11. Duree totale d'activite en heures (premier appel -> dernier appel)
    ROUND(
        EXTRACT(EPOCH FROM MAX(timestamp) - MIN(timestamp)) / 3600.0, 2
    ) AS heures_activite_totale,

    -- === FEATURES TYPE D'APPEL ===
    -- 12. Ratio d'appels sortants (SIM Box = surtout des appels sortants)
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE call_type IN ('moCallSetUp', 'outgoing', 'callForwarding'))
        / NULLIF(COUNT(*), 0), 2
    ) AS ratio_appels_sortants

FROM cdr_data
GROUP BY msisdn;

-- Index pour accelerer les requetes futures
CREATE INDEX idx_features_msisdn ON features_msisdn(msisdn);
CREATE INDEX idx_features_appels ON features_msisdn(nombre_appels DESC);
