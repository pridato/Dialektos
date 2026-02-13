-- ============================================================================
-- Migración: columnas del HUD / Active Session en study_sessions (SQLite)
-- Ejecutar una sola vez: sqlite3 data/metrics.db < scripts/db/migrate_study_sessions_hud.sql
-- ============================================================================

ALTER TABLE study_sessions ADD COLUMN subject TEXT;
ALTER TABLE study_sessions ADD COLUMN goal_description TEXT;
ALTER TABLE study_sessions ADD COLUMN task_category TEXT;
ALTER TABLE study_sessions ADD COLUMN perceived_difficulty INTEGER;
ALTER TABLE study_sessions ADD COLUMN comments TEXT;
ALTER TABLE study_sessions ADD COLUMN pre_session_energy INTEGER;
ALTER TABLE study_sessions ADD COLUMN zone TEXT;
