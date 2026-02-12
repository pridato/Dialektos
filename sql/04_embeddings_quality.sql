-- ============================================================================
-- Script 4: Calidad de Embeddings
-- ============================================================================
-- Analiza la calidad y consistencia de los embeddings almacenados

.headers on
.mode column
.width 40 15

SELECT '=== CALIDAD DE EMBEDDINGS ===' as info;

-- Verificar completitud de datos
SELECT 
    COUNT(*) as total_registros,
    COUNT(DISTINCT embedding_id) as embeddings_unicos,
    ROUND(CAST(COUNT(DISTINCT embedding_id) AS REAL) / COUNT(*) * 100, 2) as porcentaje_unicidad
FROM embeddings;

-- Verificar que todos los chunks tienen documento
SELECT '' as separador;
SELECT '=== COMPLETITUD DE DOCUMENTOS ===' as info;

SELECT 
    (SELECT COUNT(*) FROM embeddings) as total_embeddings,
    COUNT(*) as con_documento,
    (SELECT COUNT(*) FROM embeddings) - COUNT(*) as sin_documento,
    ROUND(CAST(COUNT(*) AS REAL) / (SELECT COUNT(*) FROM embeddings) * 100, 2) as porcentaje_completitud
FROM embedding_metadata
WHERE key = 'chroma:document';

-- Estadísticas de chunks vacíos o muy cortos
SELECT '' as separador;
SELECT '=== CHUNKS CON PROBLEMAS POTENCIALES ===' as info;

SELECT 
    'Chunks vacíos' as tipo_problema,
    COUNT(*) as cantidad
FROM embedding_metadata
WHERE key = 'chroma:document' 
AND (string_value IS NULL OR string_value = '' OR LENGTH(TRIM(string_value)) = 0)

UNION ALL

SELECT 
    'Chunks muy cortos (<100 chars)' as tipo_problema,
    COUNT(*) as cantidad
FROM embedding_metadata
WHERE key = 'chroma:document' AND LENGTH(string_value) < 100

UNION ALL

SELECT 
    'Chunks muy largos (>2000 chars)' as tipo_problema,
    COUNT(*) as cantidad
FROM embedding_metadata
WHERE key = 'chroma:document' AND LENGTH(string_value) > 2000;

-- Distribución de longitudes
SELECT '' as separador;
SELECT '=== DISTRIBUCIÓN DE LONGITUDES DE CHUNKS ===' as info;

SELECT 
    CASE 
        WHEN LENGTH(string_value) < 200 THEN '0-200 caracteres'
        WHEN LENGTH(string_value) < 500 THEN '200-500 caracteres'
        WHEN LENGTH(string_value) < 1000 THEN '500-1000 caracteres'
        WHEN LENGTH(string_value) < 1500 THEN '1000-1500 caracteres'
        ELSE 'Más de 1500 caracteres'
    END as rango_longitud,
    COUNT(*) as cantidad,
    ROUND(CAST(COUNT(*) AS REAL) / (SELECT COUNT(*) FROM embedding_metadata WHERE key = 'chroma:document') * 100, 2) as porcentaje
FROM embedding_metadata
WHERE key = 'chroma:document'
GROUP BY rango_longitud
ORDER BY MIN(LENGTH(string_value));

-- Chunks únicos vs duplicados
SELECT '' as separador;
SELECT '=== ANÁLISIS DE DUPLICACIÓN ===' as info;

SELECT 
    COUNT(*) as total_chunks,
    COUNT(DISTINCT string_value) as chunks_unicos,
    COUNT(*) - COUNT(DISTINCT string_value) as chunks_duplicados,
    ROUND(CAST((COUNT(*) - COUNT(DISTINCT string_value)) AS REAL) / COUNT(*) * 100, 2) as porcentaje_duplicacion
FROM embedding_metadata
WHERE key = 'chroma:document';
