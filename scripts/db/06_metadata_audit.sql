-- ============================================================================
-- Script 6: Auditoría Completa de Metadatos - ChromaDB Dialektos
-- ============================================================================
-- Radiografía del estado actual de los metadatos estructurados.
-- Muestra qué campos están poblados, cuáles faltan, y el desglose
-- por cada valor de asignatura, tipo, idioma, etc.
--
-- Ejecutar con:
--   sqlite3 data/chroma_db/chroma.sqlite3 < scripts/db/06_metadata_audit.sql
--
-- Autor: David Arroyo
-- Proyecto: Dialektos - Sistema RAG Adaptativo
-- ============================================================================

.headers on
.mode box
.width 35 12

-- ═══════════════════════════════════════════════════════════════════════════
-- SECCIÓN 1: Inventario de todas las claves de metadatos existentes
-- ═══════════════════════════════════════════════════════════════════════════

SELECT '╔══════════════════════════════════════════════════╗' as '';
SELECT '║  1. INVENTARIO DE CLAVES DE METADATOS            ║' as '';
SELECT '╚══════════════════════════════════════════════════╝' as '';

SELECT 
    key                       AS clave_metadata,
    COUNT(*)                  AS total_registros,
    CASE 
        WHEN string_value IS NOT NULL THEN 'STRING'
        WHEN int_value    IS NOT NULL THEN 'INTEGER'
        WHEN float_value  IS NOT NULL THEN 'FLOAT'
        WHEN bool_value   IS NOT NULL THEN 'BOOLEAN'
        ELSE 'NULL/MIXTO'
    END                       AS tipo_dato,
    ROUND(
        CAST(COUNT(*) AS REAL) / 
        (SELECT COUNT(*) FROM embeddings) * 100, 1
    ) || '%'                  AS cobertura
FROM embedding_metadata
WHERE key NOT LIKE 'chroma:%'   -- excluir claves internas de ChromaDB
GROUP BY key
ORDER BY total_registros DESC;


-- ═══════════════════════════════════════════════════════════════════════════
-- SECCIÓN 2: Cobertura de metadatos estructurados (StructuredMetadata)
-- ═══════════════════════════════════════════════════════════════════════════

SELECT '';
SELECT '╔══════════════════════════════════════════════════╗' as '';
SELECT '║  2. COBERTURA DE METADATOS ESTRUCTURADOS         ║' as '';
SELECT '╚══════════════════════════════════════════════════╝' as '';

-- Los campos de StructuredMetadata que deberían estar poblados
WITH total AS (
    SELECT COUNT(*) AS n FROM embeddings
),
campo_counts AS (
    SELECT 'filename'          AS campo, COUNT(*) AS poblados FROM embedding_metadata WHERE key = 'filename'
    UNION ALL
    SELECT 'source_folder',             COUNT(*) FROM embedding_metadata WHERE key = 'source_folder'
    UNION ALL
    SELECT 'page_number',               COUNT(*) FROM embedding_metadata WHERE key = 'page_number'
    UNION ALL
    SELECT 'total_pages',               COUNT(*) FROM embedding_metadata WHERE key = 'total_pages'
    UNION ALL
    SELECT 'asignatura',                COUNT(*) FROM embedding_metadata WHERE key = 'asignatura'
    UNION ALL
    SELECT 'tipo',                      COUNT(*) FROM embedding_metadata WHERE key = 'tipo'
    UNION ALL
    SELECT 'fecha',                     COUNT(*) FROM embedding_metadata WHERE key = 'fecha'
    UNION ALL
    SELECT 'idioma',                    COUNT(*) FROM embedding_metadata WHERE key = 'idioma'
    UNION ALL
    SELECT 'autor',                     COUNT(*) FROM embedding_metadata WHERE key = 'autor'
    UNION ALL
    SELECT 'nivel_dificultad',          COUNT(*) FROM embedding_metadata WHERE key = 'nivel_dificultad'
    UNION ALL
    SELECT 'tema_especifico',           COUNT(*) FROM embedding_metadata WHERE key = 'tema_especifico'
    UNION ALL
    SELECT 'chunk_index',               COUNT(*) FROM embedding_metadata WHERE key = 'chunk_index'
    UNION ALL
    SELECT 'total_chunks',              COUNT(*) FROM embedding_metadata WHERE key = 'total_chunks'
    UNION ALL
    SELECT 'char_count',                COUNT(*) FROM embedding_metadata WHERE key = 'char_count'
    UNION ALL
    SELECT 'token_count',               COUNT(*) FROM embedding_metadata WHERE key = 'token_count'
)
SELECT 
    c.campo,
    c.poblados                          AS chunks_con_valor,
    t.n - c.poblados                    AS chunks_sin_valor,
    ROUND(CAST(c.poblados AS REAL) / t.n * 100, 1) || '%' AS cobertura,
    CASE 
        WHEN c.poblados = t.n                              THEN '✅ Completo'
        WHEN c.poblados = 0                                THEN '❌ Vacío'
        WHEN CAST(c.poblados AS REAL) / t.n >= 0.8         THEN '🟡 Parcial (>80%)'
        ELSE '🔴 Bajo (<80%)'
    END                                 AS estado
FROM campo_counts c, total t
ORDER BY 
    CASE 
        WHEN c.poblados = t.n THEN 0
        WHEN c.poblados = 0   THEN 2
        ELSE 1
    END,
    c.campo;


-- ═══════════════════════════════════════════════════════════════════════════
-- SECCIÓN 3: Desglose de valores por campo estructurado
-- ═══════════════════════════════════════════════════════════════════════════

SELECT '';
SELECT '╔══════════════════════════════════════════════════╗' as '';
SELECT '║  3a. DESGLOSE POR ASIGNATURA                     ║' as '';
SELECT '╚══════════════════════════════════════════════════╝' as '';

SELECT 
    COALESCE(string_value, '(sin asignatura)') AS asignatura,
    COUNT(*)                                    AS chunks,
    ROUND(CAST(COUNT(*) AS REAL) / (SELECT COUNT(*) FROM embeddings) * 100, 1) || '%' AS porcentaje
FROM embedding_metadata
WHERE key = 'asignatura'
GROUP BY string_value
ORDER BY chunks DESC;


SELECT '';
SELECT '╔══════════════════════════════════════════════════╗' as '';
SELECT '║  3b. DESGLOSE POR TIPO DE MATERIAL               ║' as '';
SELECT '╚══════════════════════════════════════════════════╝' as '';

SELECT 
    COALESCE(string_value, '(sin tipo)') AS tipo_material,
    COUNT(*)                              AS chunks,
    ROUND(CAST(COUNT(*) AS REAL) / (SELECT COUNT(*) FROM embeddings) * 100, 1) || '%' AS porcentaje
FROM embedding_metadata
WHERE key = 'tipo'
GROUP BY string_value
ORDER BY chunks DESC;


SELECT '';
SELECT '╔══════════════════════════════════════════════════╗' as '';
SELECT '║  3c. DESGLOSE POR IDIOMA                         ║' as '';
SELECT '╚══════════════════════════════════════════════════╝' as '';

SELECT 
    COALESCE(string_value, '(sin idioma)') AS idioma,
    COUNT(*)                                AS chunks,
    ROUND(CAST(COUNT(*) AS REAL) / (SELECT COUNT(*) FROM embeddings) * 100, 1) || '%' AS porcentaje
FROM embedding_metadata
WHERE key = 'idioma'
GROUP BY string_value
ORDER BY chunks DESC;


SELECT '';
SELECT '╔══════════════════════════════════════════════════╗' as '';
SELECT '║  3d. DESGLOSE POR NIVEL DE DIFICULTAD            ║' as '';
SELECT '╚══════════════════════════════════════════════════╝' as '';

SELECT 
    COALESCE(string_value, '(sin nivel)') AS nivel_dificultad,
    COUNT(*)                               AS chunks,
    ROUND(CAST(COUNT(*) AS REAL) / (SELECT COUNT(*) FROM embeddings) * 100, 1) || '%' AS porcentaje
FROM embedding_metadata
WHERE key = 'nivel_dificultad'
GROUP BY string_value
ORDER BY chunks DESC;


SELECT '';
SELECT '╔══════════════════════════════════════════════════╗' as '';
SELECT '║  3e. DESGLOSE POR TEMA ESPECÍFICO                ║' as '';
SELECT '╚══════════════════════════════════════════════════╝' as '';

SELECT 
    COALESCE(string_value, '(sin tema)') AS tema_especifico,
    COUNT(*)                              AS chunks,
    ROUND(CAST(COUNT(*) AS REAL) / (SELECT COUNT(*) FROM embeddings) * 100, 1) || '%' AS porcentaje
FROM embedding_metadata
WHERE key = 'tema_especifico'
GROUP BY string_value
ORDER BY chunks DESC;


SELECT '';
SELECT '╔══════════════════════════════════════════════════╗' as '';
SELECT '║  3f. DESGLOSE POR AUTOR                          ║' as '';
SELECT '╚══════════════════════════════════════════════════╝' as '';

SELECT 
    COALESCE(string_value, '(sin autor)') AS autor,
    COUNT(*)                               AS chunks,
    ROUND(CAST(COUNT(*) AS REAL) / (SELECT COUNT(*) FROM embeddings) * 100, 1) || '%' AS porcentaje
FROM embedding_metadata
WHERE key = 'autor'
GROUP BY string_value
ORDER BY chunks DESC;


SELECT '';
SELECT '╔══════════════════════════════════════════════════╗' as '';
SELECT '║  3g. DESGLOSE POR FECHA                          ║' as '';
SELECT '╚══════════════════════════════════════════════════╝' as '';

SELECT 
    COALESCE(string_value, '(sin fecha)') AS fecha,
    COUNT(*)                               AS chunks,
    ROUND(CAST(COUNT(*) AS REAL) / (SELECT COUNT(*) FROM embeddings) * 100, 1) || '%' AS porcentaje
FROM embedding_metadata
WHERE key = 'fecha'
GROUP BY string_value
ORDER BY chunks DESC;


-- ═══════════════════════════════════════════════════════════════════════════
-- SECCIÓN 4: Cobertura cruzada por archivo (¿qué archivos tienen qué?)
-- ═══════════════════════════════════════════════════════════════════════════

SELECT '';
SELECT '╔══════════════════════════════════════════════════╗' as '';
SELECT '║  4. COBERTURA POR ARCHIVO (metadatos enriquecidos)║' as '';
SELECT '╚══════════════════════════════════════════════════╝' as '';

-- Para cada archivo: ¿tiene asignatura, tipo, idioma poblados?
WITH archivos AS (
    SELECT DISTINCT id, string_value AS filename
    FROM embedding_metadata
    WHERE key = 'filename'
),
asig AS (
    SELECT id FROM embedding_metadata WHERE key = 'asignatura' AND string_value IS NOT NULL
),
tipo AS (
    SELECT id FROM embedding_metadata WHERE key = 'tipo' AND string_value IS NOT NULL
),
idioma AS (
    SELECT id FROM embedding_metadata WHERE key = 'idioma' AND string_value IS NOT NULL
)
SELECT 
    a.filename,
    COUNT(*)                                                    AS total_chunks,
    SUM(CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END)          AS con_asignatura,
    SUM(CASE WHEN t.id IS NOT NULL THEN 1 ELSE 0 END)          AS con_tipo,
    SUM(CASE WHEN i.id IS NOT NULL THEN 1 ELSE 0 END)          AS con_idioma,
    CASE 
        WHEN SUM(CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END) = COUNT(*)
         AND SUM(CASE WHEN t.id IS NOT NULL THEN 1 ELSE 0 END) = COUNT(*)
         AND SUM(CASE WHEN i.id IS NOT NULL THEN 1 ELSE 0 END) = COUNT(*)
        THEN '✅'
        WHEN SUM(CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END) = 0
         AND SUM(CASE WHEN t.id IS NOT NULL THEN 1 ELSE 0 END) = 0
         AND SUM(CASE WHEN i.id IS NOT NULL THEN 1 ELSE 0 END) = 0
        THEN '❌'
        ELSE '🟡'
    END                                                          AS estado_metadata
FROM archivos a
LEFT JOIN asig   s ON a.id = s.id
LEFT JOIN tipo   t ON a.id = t.id
LEFT JOIN idioma i ON a.id = i.id
GROUP BY a.filename
ORDER BY estado_metadata, a.filename;


-- ═══════════════════════════════════════════════════════════════════════════
-- SECCIÓN 5: Archivos por carpeta de origen (source_folder)
-- ═══════════════════════════════════════════════════════════════════════════

SELECT '';
SELECT '╔══════════════════════════════════════════════════╗' as '';
SELECT '║  5. DISTRIBUCIÓN POR CARPETA DE ORIGEN           ║' as '';
SELECT '╚══════════════════════════════════════════════════╝' as '';

SELECT 
    string_value                                                AS source_folder,
    COUNT(*)                                                    AS chunks,
    COUNT(DISTINCT id)                                          AS chunks_unicos,
    ROUND(CAST(COUNT(*) AS REAL) / (SELECT COUNT(*) FROM embeddings) * 100, 1) || '%' AS porcentaje
FROM embedding_metadata
WHERE key = 'source_folder'
GROUP BY string_value
ORDER BY chunks DESC;


-- ═══════════════════════════════════════════════════════════════════════════
-- SECCIÓN 6: Matriz asignatura × tipo (si ambos están poblados)
-- ═══════════════════════════════════════════════════════════════════════════

SELECT '';
SELECT '╔══════════════════════════════════════════════════╗' as '';
SELECT '║  6. MATRIZ CRUZADA: ASIGNATURA × TIPO            ║' as '';
SELECT '╚══════════════════════════════════════════════════╝' as '';

SELECT 
    a.string_value AS asignatura,
    t.string_value AS tipo,
    COUNT(*)       AS chunks
FROM embedding_metadata a
JOIN embedding_metadata t ON a.id = t.id AND t.key = 'tipo'
WHERE a.key = 'asignatura'
GROUP BY a.string_value, t.string_value
ORDER BY a.string_value, chunks DESC;


-- ═══════════════════════════════════════════════════════════════════════════
-- SECCIÓN 7: Muestra de metadatos completos de un chunk por archivo
-- ═══════════════════════════════════════════════════════════════════════════

SELECT '';
SELECT '╔══════════════════════════════════════════════════╗' as '';
SELECT '║  7. MUESTRA: METADATOS COMPLETOS (1 chunk/archivo)║' as '';
SELECT '╚══════════════════════════════════════════════════╝' as '';

.mode column
.width 16 25 15 8 12 10 10 10 10 15

WITH sample_ids AS (
    -- Elegir 1 chunk representativo por cada archivo
    SELECT MIN(id) AS id, string_value AS filename
    FROM embedding_metadata
    WHERE key = 'filename'
    GROUP BY string_value
)
SELECT 
    s.id                                                         AS chunk_id,
    s.filename,
    COALESCE(sf.string_value, '-')                               AS source_folder,
    COALESCE(CAST(pn.int_value AS TEXT), '-')                    AS pagina,
    COALESCE(asig.string_value, '-')                             AS asignatura,
    COALESCE(tipo.string_value, '-')                             AS tipo,
    COALESCE(idioma.string_value, '-')                           AS idioma,
    COALESCE(nivel.string_value, '-')                            AS nivel,
    COALESCE(tema.string_value, '-')                             AS tema,
    COALESCE(autor.string_value, '-')                            AS autor
FROM sample_ids s
LEFT JOIN embedding_metadata sf     ON s.id = sf.id    AND sf.key    = 'source_folder'
LEFT JOIN embedding_metadata pn     ON s.id = pn.id    AND pn.key    = 'page_number'
LEFT JOIN embedding_metadata asig   ON s.id = asig.id  AND asig.key  = 'asignatura'
LEFT JOIN embedding_metadata tipo   ON s.id = tipo.id  AND tipo.key  = 'tipo'
LEFT JOIN embedding_metadata idioma ON s.id = idioma.id AND idioma.key = 'idioma'
LEFT JOIN embedding_metadata nivel  ON s.id = nivel.id AND nivel.key = 'nivel_dificultad'
LEFT JOIN embedding_metadata tema   ON s.id = tema.id  AND tema.key  = 'tema_especifico'
LEFT JOIN embedding_metadata autor  ON s.id = autor.id AND autor.key = 'autor'
ORDER BY s.filename;


-- ═══════════════════════════════════════════════════════════════════════════
-- SECCIÓN 8: Resumen ejecutivo
-- ═══════════════════════════════════════════════════════════════════════════

SELECT '';
SELECT '╔══════════════════════════════════════════════════╗' as '';
SELECT '║  8. RESUMEN EJECUTIVO                            ║' as '';
SELECT '╚══════════════════════════════════════════════════╝' as '';

.mode box
.width 40 15

WITH total AS (SELECT COUNT(*) AS n FROM embeddings),
     files AS (SELECT COUNT(DISTINCT string_value) AS n FROM embedding_metadata WHERE key = 'filename'),
     folders AS (SELECT COUNT(DISTINCT string_value) AS n FROM embedding_metadata WHERE key = 'source_folder'),
     asig_c AS (SELECT COUNT(*) AS n FROM embedding_metadata WHERE key = 'asignatura'),
     tipo_c AS (SELECT COUNT(*) AS n FROM embedding_metadata WHERE key = 'tipo'),
     idioma_c AS (SELECT COUNT(*) AS n FROM embedding_metadata WHERE key = 'idioma'),
     nivel_c AS (SELECT COUNT(*) AS n FROM embedding_metadata WHERE key = 'nivel_dificultad'),
     tema_c AS (SELECT COUNT(*) AS n FROM embedding_metadata WHERE key = 'tema_especifico'),
     autor_c AS (SELECT COUNT(*) AS n FROM embedding_metadata WHERE key = 'autor')
SELECT 'Total chunks en ChromaDB' AS metrica, CAST(t.n AS TEXT) AS valor FROM total t
UNION ALL SELECT 'Archivos PDF únicos',       CAST(f.n AS TEXT) FROM files f
UNION ALL SELECT 'Carpetas de origen',         CAST(fo.n AS TEXT) FROM folders fo
UNION ALL SELECT '---', '---'
UNION ALL SELECT 'Cobertura: asignatura',      ROUND(CAST(a.n AS REAL) / t.n * 100, 1) || '% (' || a.n || '/' || t.n || ')' FROM asig_c a, total t
UNION ALL SELECT 'Cobertura: tipo',            ROUND(CAST(tp.n AS REAL) / t.n * 100, 1) || '% (' || tp.n || '/' || t.n || ')' FROM tipo_c tp, total t
UNION ALL SELECT 'Cobertura: idioma',          ROUND(CAST(i.n AS REAL) / t.n * 100, 1) || '% (' || i.n || '/' || t.n || ')' FROM idioma_c i, total t
UNION ALL SELECT 'Cobertura: nivel_dificultad',ROUND(CAST(nv.n AS REAL) / t.n * 100, 1) || '% (' || nv.n || '/' || t.n || ')' FROM nivel_c nv, total t
UNION ALL SELECT 'Cobertura: tema_especifico', ROUND(CAST(te.n AS REAL) / t.n * 100, 1) || '% (' || te.n || '/' || t.n || ')' FROM tema_c te, total t
UNION ALL SELECT 'Cobertura: autor',           ROUND(CAST(au.n AS REAL) / t.n * 100, 1) || '% (' || au.n || '/' || t.n || ')' FROM autor_c au, total t;


SELECT '';
SELECT '═══════════════════════════════════════════════════' as '';
SELECT '  FIN DE LA AUDITORÍA DE METADATOS                 ' as '';
SELECT '═══════════════════════════════════════════════════' as '';
