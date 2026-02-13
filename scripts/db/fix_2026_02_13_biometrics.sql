-- Actualiza el registro 2026-02-13 con datos de suunto_data.json
-- (hrv_rmssd=63 → ln_rmssd=ln(63), sleep_quality=80, body_resources=72)
-- Ejecutar: sqlite3 data/metrics.db < scripts/db/fix_2026_02_13_biometrics.sql

UPDATE daily_biometrics
SET
    hrv_rmssd = 63,
    ln_rmssd = 4.143134726391533,
    sleep_quality = 80,
    body_resources = 72
WHERE date = '2026-02-13';
