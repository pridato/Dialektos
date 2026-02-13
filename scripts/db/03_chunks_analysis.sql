-- ============================================================================
-- Script 3: Análisis Detallado de Chunks y Embeddings
-- ============================================================================
-- Analiza el contenido de los chunks almacenados

.headers on
.mode column
.width 10 50 15

SELECT '=== RESUMEN GENERAL DE CHUNKS ===' as info;

-- Estadísticas generales
SELECT 
    COUNT(*) as total_chunks,
    COUNT(DISTINCT embedding_id) as embeddings_unicos
FROM embeddings;

-- Análisis de longitud de documentos (desde metadatos)
SELECT '' as separador;
SELECT '=== ESTADÍSTICAS DE LONGITUD DE TEXTO ===' as info;

SELECT 
    COUNT(*) as total_documentos,
    MIN(LENGTH(string_value)) as min_longitud,
    MAX(LENGTH(string_value)) as max_longitud,
    ROUND(AVG(LENGTH(string_value)), 2) as promedio_longitud
FROM embedding_metadata
WHERE key = 'chroma:document';

-- Distribución por archivo
SELECT '' as separador;
SELECT '=== CHUNKS POR ARCHIVO ===' as info;

SELECT 
    string_value as archivo,
    COUNT(*) as cantidad_chunks
FROM embedding_metadata
WHERE key = 'filename'
GROUP BY string_value
ORDER BY cantidad_chunks DESC;

-- Análisis de metadatos
SELECT '' as separador;
SELECT '=== TIPOS DE METADATOS DISPONIBLES ===' as info;

SELECT 
    key as tipo_metadata,
    COUNT(*) as cantidad,
    CASE 
        WHEN string_value IS NOT NULL THEN 'string'
        WHEN int_value IS NOT NULL THEN 'integer'
        WHEN float_value IS NOT NULL THEN 'float'
        WHEN bool_value IS NOT NULL THEN 'boolean'
    END as tipo_valor
FROM embedding_metadata
GROUP BY key
ORDER BY cantidad DESC;

-- Muestra de chunks (primeros 5)
SELECT '' as separador;
SELECT '=== MUESTRA DE CHUNKS (5 primeros) ===' as info;

SELECT 
    e.id as chunk_id,
    SUBSTR(m.string_value, 1, 100) || '...' as texto,
    LENGTH(m.string_value) as longitud
FROM embeddings e
JOIN embedding_metadata m ON e.id = m.id AND m.key = 'chroma:document'
LIMIT 5;
