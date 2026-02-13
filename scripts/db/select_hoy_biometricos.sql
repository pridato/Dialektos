-- ============================================================================
-- SELECT del día de hoy: VFC, calidad de sueño, batería corporal (recursos),
-- estado de recuperación (ICD).
-- Tabla: daily_biometrics (módulo Bio-Adaptabilidad - Dialektos)
-- ============================================================================
-- Uso: sqlite3 data/metrics.db < scripts/db/select_hoy_biometricos.sql
-- ============================================================================

SELECT
    date AS fecha,
    ln_rmssd AS vfc_ln_rmssd,
    sleep_quality AS calidad_sueno,
    body_resources AS bateria_corporal_recursos,
    ROUND(icd_score, 2) AS estado_recuperacion_icd
FROM daily_biometrics
WHERE date = DATE('now', 'localtime');
