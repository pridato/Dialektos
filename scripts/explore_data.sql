-- ============================================================================
-- SCRIPT DE EXPLORACIÓN DE DATOS - Módulo Bio-Adaptabilidad
-- Proyecto Dialektos
-- ============================================================================
-- 
-- Este script permite explorar todos los datos almacenados en metrics.db
-- Incluye consultas para ver la estructura, datos insertados, métricas
-- calculadas y análisis básicos.
--
-- Uso:
--   sqlite3 data/metrics.db < scripts/explore_data.sql
--   O desde Python: sqlite3.connect('data/metrics.db').executescript(open('scripts/explore_data.sql').read())
--
-- Autor: David Arroyo
-- Fecha: 2026-02-13
-- ============================================================================

.headers on
.mode column
.width 15 15 15 15 15 15 15 15

-- ============================================================================
-- 1. ESTRUCTURA DE LA BASE DE DATOS
-- ============================================================================

.print "\n═══════════════════════════════════════════════════════════════════════"
.print "1. ESTRUCTURA DE TABLAS"
.print "═══════════════════════════════════════════════════════════════════════\n"

.print "Tabla: daily_biometrics"
.schema daily_biometrics

.print "\nTabla: study_sessions"
.schema study_sessions

.print "\nTabla: daily_confounders"
.schema daily_confounders

-- ============================================================================
-- 2. RESUMEN DE DATOS (CONTEOS)
-- ============================================================================

.print "\n═══════════════════════════════════════════════════════════════════════"
.print "2. RESUMEN DE DATOS"
.print "═══════════════════════════════════════════════════════════════════════\n"

SELECT 
    'daily_biometrics' AS tabla,
    COUNT(*) AS total_registros,
    MIN(date) AS fecha_minima,
    MAX(date) AS fecha_maxima,
    COUNT(DISTINCT date) AS dias_unicos
FROM daily_biometrics

UNION ALL

SELECT 
    'study_sessions' AS tabla,
    COUNT(*) AS total_registros,
    MIN(date) AS fecha_minima,
    MAX(date) AS fecha_maxima,
    COUNT(DISTINCT date) AS dias_unicos
FROM study_sessions

UNION ALL

SELECT 
    'daily_confounders' AS tabla,
    COUNT(*) AS total_registros,
    MIN(date) AS fecha_minima,
    MAX(date) AS fecha_maxima,
    COUNT(DISTINCT date) AS dias_unicos
FROM daily_confounders;

-- ============================================================================
-- 3. DATOS COMPLETOS DE DAILY_BIOMETRICS
-- ============================================================================

.print "\n═══════════════════════════════════════════════════════════════════════"
.print "3. DATOS COMPLETOS - DailyBiometrics"
.print "═══════════════════════════════════════════════════════════════════════\n"

SELECT 
    date,
    hrv_rmssd,
    ROUND(ln_rmssd, 3) AS ln_rmssd,
    ROUND(hrv_baseline_7d, 3) AS hrv_baseline_7d,
    resting_hr,
    sleep_total_min,
    sleep_quality,
    body_resources,
    energy_level,
    mental_clarity,
    mood,
    ROUND(icd_score, 2) AS icd_score
FROM daily_biometrics
ORDER BY date DESC;

-- ============================================================================
-- 4. MÉTRICAS DERIVADAS CALCULADAS
-- ============================================================================

.print "\n═══════════════════════════════════════════════════════════════════════"
.print "4. MÉTRICAS DERIVADAS (Feature Engineering - Tarea 3.3)"
.print "═══════════════════════════════════════════════════════════════════════\n"

SELECT 
    date,
    hrv_rmssd AS hrv_raw_ms,
    ROUND(ln_rmssd, 4) AS ln_rmssd,
    ROUND(hrv_baseline_7d, 4) AS baseline_7d_ema,
    ROUND(hrv_baseline_7d - ln_rmssd, 4) AS desviacion_del_baseline,
    ROUND(sleep_consistency, 2) AS sleep_consistency_min,
    ROUND(icd_score, 2) AS icd_score
FROM daily_biometrics
WHERE ln_rmssd IS NOT NULL OR hrv_baseline_7d IS NOT NULL OR icd_score IS NOT NULL
ORDER BY date DESC;

-- ============================================================================
-- 5. ANÁLISIS DEL ICD (Índice Cognitivo Diario - Tarea 3.4)
-- ============================================================================

.print "\n═══════════════════════════════════════════════════════════════════════"
.print "5. ANÁLISIS DEL ICD (Índice Cognitivo Diario)"
.print "═══════════════════════════════════════════════════════════════════════\n"

-- Estadísticas del ICD
SELECT 
    COUNT(*) AS dias_con_icd,
    ROUND(AVG(icd_score), 2) AS icd_promedio,
    ROUND(MIN(icd_score), 2) AS icd_minimo,
    ROUND(MAX(icd_score), 2) AS icd_maximo,
    ROUND(STDEV(icd_score), 2) AS icd_desviacion_std
FROM daily_biometrics
WHERE icd_score IS NOT NULL;

-- Distribución del ICD por rangos
.print "\nDistribución del ICD por rangos:\n"

SELECT 
    CASE 
        WHEN icd_score >= 80 THEN 'Peak (80-100)'
        WHEN icd_score >= 50 THEN 'Normal (50-80)'
        WHEN icd_score >= 30 THEN 'Fatigue (30-50)'
        ELSE 'Burnout (<30)'
    END AS rango_icd,
    COUNT(*) AS cantidad_dias,
    ROUND(AVG(icd_score), 2) AS promedio_icd
FROM daily_biometrics
WHERE icd_score IS NOT NULL
GROUP BY rango_icd
ORDER BY MIN(icd_score) DESC;

-- Componentes del ICD (últimos 7 días)
.print "\nComponentes del ICD (últimos 7 días):\n"

SELECT 
    date,
    ROUND(ln_rmssd, 3) AS ln_rmssd,
    sleep_quality,
    body_resources,
    energy_level,
    mental_clarity,
    mood,
    ROUND(icd_score, 2) AS icd_score
FROM daily_biometrics
WHERE icd_score IS NOT NULL
ORDER BY date DESC
LIMIT 7;

-- ============================================================================
-- 6. SESIONES DE ESTUDIO (StudySession)
-- ============================================================================

.print "\n═══════════════════════════════════════════════════════════════════════"
.print "6. SESIONES DE ESTUDIO"
.print "═══════════════════════════════════════════════════════════════════════\n"

SELECT 
    session_id,
    date,
    datetime(start_time) AS inicio,
    datetime(end_time) AS fin,
    duration_min AS duracion_min,
    task_type AS tipo_tarea,
    difficulty_attempted AS dificultad,
    focus_score AS focus,
    comprehension_rate AS comprension_pct,
    flow_state AS flow,
    ROUND(icd_at_start, 2) AS icd_al_inicio
FROM study_sessions
ORDER BY date DESC, start_time DESC;

-- Estadísticas de sesiones
.print "\nEstadísticas de sesiones:\n"

SELECT 
    COUNT(*) AS total_sesiones,
    COUNT(DISTINCT date) AS dias_con_sesiones,
    ROUND(AVG(duration_min), 1) AS duracion_promedio_min,
    ROUND(AVG(focus_score), 2) AS focus_promedio,
    ROUND(AVG(comprehension_rate), 1) AS comprension_promedio_pct,
    SUM(CASE WHEN flow_state = 1 THEN 1 ELSE 0 END) AS sesiones_en_flow,
    ROUND(AVG(icd_at_start), 2) AS icd_promedio_al_inicio
FROM study_sessions;

-- ============================================================================
-- 7. VARIABLES DE CONFUSIÓN (DailyConfounders)
-- ============================================================================

.print "\n═══════════════════════════════════════════════════════════════════════"
.print "7. VARIABLES DE CONFUSIÓN"
.print "═══════════════════════════════════════════════════════════════════════\n"

SELECT 
    date,
    caffeine_mg AS cafeina_mg,
    screen_time_pre_sleep AS pantalla_pre_sueno_min,
    meals_quality AS calidad_comidas,
    social_stress AS estres_social,
    exercise_type AS tipo_ejercicio,
    exercise_min AS ejercicio_min,
    notes AS notas
FROM daily_confounders
ORDER BY date DESC;

-- ============================================================================
-- 8. JOIN: BIOMÉTRICAS + SESIONES + CONFOUNDERS
-- ============================================================================

.print "\n═══════════════════════════════════════════════════════════════════════"
.print "8. VISTA INTEGRADA (Biométricas + Sesiones + Confounders)"
.print "═══════════════════════════════════════════════════════════════════════\n"

SELECT 
    db.date,
    ROUND(db.icd_score, 2) AS icd_score,
    db.energy_level AS energia,
    db.mental_clarity AS claridad,
    db.mood AS animo,
    COUNT(ss.session_id) AS num_sesiones,
    ROUND(AVG(ss.focus_score), 2) AS focus_promedio,
    ROUND(AVG(ss.comprehension_rate), 1) AS comprension_promedio,
    dc.caffeine_mg AS cafeina_mg,
    dc.exercise_type AS ejercicio
FROM daily_biometrics db
LEFT JOIN study_sessions ss ON db.date = ss.date
LEFT JOIN daily_confounders dc ON db.date = dc.date
WHERE db.icd_score IS NOT NULL
GROUP BY db.date
ORDER BY db.date DESC
LIMIT 10;

-- ============================================================================
-- 9. CORRELACIONES BÁSICAS (Análisis Exploratorio)
-- ============================================================================

.print "\n═══════════════════════════════════════════════════════════════════════"
.print "9. ANÁLISIS EXPLORATORIO - Correlaciones"
.print "═══════════════════════════════════════════════════════════════════════\n"

-- ICD vs Focus Score
.print "ICD vs Focus Score (últimas sesiones):\n"

SELECT 
    ss.date,
    ROUND(db.icd_score, 2) AS icd_score,
    ss.focus_score,
    ss.comprehension_rate AS comprension,
    ss.flow_state AS flow
FROM study_sessions ss
JOIN daily_biometrics db ON ss.date = db.date
WHERE db.icd_score IS NOT NULL AND ss.focus_score IS NOT NULL
ORDER BY ss.date DESC, ss.start_time DESC
LIMIT 10;

-- HRV vs Rendimiento
.print "\nHRV (ln_rmssd) vs Rendimiento:\n"

SELECT 
    db.date,
    ROUND(db.ln_rmssd, 3) AS ln_rmssd,
    ROUND(db.icd_score, 2) AS icd_score,
    ROUND(AVG(ss.focus_score), 2) AS focus_promedio,
    ROUND(AVG(ss.comprehension_rate), 1) AS comprension_promedio
FROM daily_biometrics db
LEFT JOIN study_sessions ss ON db.date = ss.date
WHERE db.ln_rmssd IS NOT NULL
GROUP BY db.date
ORDER BY db.date DESC
LIMIT 10;

-- ============================================================================
-- 10. VALIDACIÓN DE DATOS (Detección de problemas)
-- ============================================================================

.print "\n═══════════════════════════════════════════════════════════════════════"
.print "10. VALIDACIÓN DE DATOS"
.print "═══════════════════════════════════════════════════════════════════════\n"

-- Días sin métricas derivadas calculadas
.print "Días con datos pero sin métricas derivadas:\n"

SELECT 
    date,
    hrv_rmssd,
    CASE WHEN ln_rmssd IS NULL THEN 'FALTA ln_rmssd' ELSE 'OK' END AS ln_rmssd_status,
    CASE WHEN hrv_baseline_7d IS NULL THEN 'FALTA baseline' ELSE 'OK' END AS baseline_status,
    CASE WHEN icd_score IS NULL THEN 'FALTA ICD' ELSE 'OK' END AS icd_status
FROM daily_biometrics
WHERE hrv_rmssd IS NOT NULL 
  AND (ln_rmssd IS NULL OR hrv_baseline_7d IS NULL OR icd_score IS NULL)
ORDER BY date DESC;

-- Sesiones sin ICD al inicio
.print "\nSesiones sin ICD al inicio capturado:\n"

SELECT 
    session_id,
    date,
    datetime(start_time) AS inicio,
    icd_at_start
FROM study_sessions
WHERE icd_at_start IS NULL
ORDER BY date DESC;

-- ============================================================================
-- 11. RESUMEN FINAL
-- ============================================================================

.print "\n═══════════════════════════════════════════════════════════════════════"
.print "11. RESUMEN FINAL"
.print "═══════════════════════════════════════════════════════════════════════\n"

SELECT 
    'Total días con biométricas' AS metrica,
    COUNT(*) AS valor
FROM daily_biometrics

UNION ALL

SELECT 
    'Días con ICD calculado',
    COUNT(*)
FROM daily_biometrics
WHERE icd_score IS NOT NULL

UNION ALL

SELECT 
    'Total sesiones de estudio',
    COUNT(*)
FROM study_sessions

UNION ALL

SELECT 
    'Días con confounders registrados',
    COUNT(*)
FROM daily_confounders

UNION ALL

SELECT 
    'ICD promedio (últimos 7 días)',
    ROUND(AVG(icd_score), 2)
FROM daily_biometrics
WHERE icd_score IS NOT NULL
  AND date >= date('now', '-7 days');

.print "\n═══════════════════════════════════════════════════════════════════════"
.print "FIN DEL REPORTE"
.print "═══════════════════════════════════════════════════════════════════════\n"
