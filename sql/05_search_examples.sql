-- ============================================================================
-- Script 5: Ejemplos de Búsqueda en Chunks
-- ============================================================================
-- Scripts para buscar y filtrar chunks específicos

.headers on
.mode column
.width 10 70 10

SELECT '=== BÚSQUEDA FULL-TEXT: "matrix" ===' as info;

-- Buscar chunks usando el índice FTS
SELECT 
    m.id as chunk_id,
    SUBSTR(m.string_value, 1, 120) || '...' as texto,
    LENGTH(m.string_value) as longitud
FROM embedding_fulltext_search fts
JOIN embedding_metadata m ON fts.rowid = m.id
WHERE fts.string_value MATCH 'matrix'
AND m.key = 'chroma:document'
LIMIT 5;

SELECT '' as separador;
SELECT '=== BÚSQUEDA FULL-TEXT: "calculus OR derivative" ===' as info;

SELECT 
    m.id as chunk_id,
    SUBSTR(m.string_value, 1, 120) || '...' as texto,
    LENGTH(m.string_value) as longitud
FROM embedding_fulltext_search fts
JOIN embedding_metadata m ON fts.rowid = m.id
WHERE fts.string_value MATCH 'calculus OR derivative'
AND m.key = 'chroma:document'
LIMIT 5;

SELECT '' as separador;
SELECT '=== BÚSQUEDA: "linear algebra" ===' as info;

SELECT 
    m.id as chunk_id,
    SUBSTR(m.string_value, 1, 120) || '...' as texto,
    LENGTH(m.string_value) as longitud
FROM embedding_fulltext_search fts
JOIN embedding_metadata m ON fts.rowid = m.id
WHERE fts.string_value MATCH 'linear algebra'
AND m.key = 'chroma:document'
LIMIT 5;

SELECT '' as separador;
SELECT '=== BÚSQUEDA: "probability" ===' as info;

SELECT 
    m.id as chunk_id,
    SUBSTR(m.string_value, 1, 120) || '...' as texto,
    LENGTH(m.string_value) as longitud
FROM embedding_fulltext_search fts
JOIN embedding_metadata m ON fts.rowid = m.id
WHERE fts.string_value MATCH 'probability'
AND m.key = 'chroma:document'
LIMIT 5;

-- Metadatos de ejemplo
SELECT '' as separador;
SELECT '=== MUESTRA DE METADATOS COMPLETOS (3 chunks) ===' as info;

SELECT 
    e.id as chunk_id,
    m1.string_value as filename,
    m2.int_value as page_number,
    SUBSTR(m3.string_value, 1, 80) || '...' as texto_preview
FROM embeddings e
LEFT JOIN embedding_metadata m1 ON e.id = m1.id AND m1.key = 'filename'
LEFT JOIN embedding_metadata m2 ON e.id = m2.id AND m2.key = 'page_number'
LEFT JOIN embedding_metadata m3 ON e.id = m3.id AND m3.key = 'chroma:document'
LIMIT 3;
