-- ============================================================================
-- Script de Estadísticas Rápidas - ChromaDB Dialektos
-- ============================================================================
-- Genera un resumen rápido del estado de la base de datos

.headers on
.mode box
.width 40 15

SELECT '═══════════════════════════════════════════' as '🎯 RESUMEN RÁPIDO - CHROMADB DIALEKTOS';
SELECT '';

-- Estadísticas generales
SELECT 'Total de Embeddings' as Métrica, COUNT(*) as Valor FROM embeddings
UNION ALL
SELECT 'Embeddings Únicos', COUNT(DISTINCT embedding_id) FROM embeddings
UNION ALL
SELECT 'Chunks con Texto', COUNT(*) FROM embedding_metadata WHERE key = 'chroma:document'
UNION ALL
SELECT 'Dimensiones', (SELECT dimension FROM collections LIMIT 1);

SELECT '';
SELECT '📏 LONGITUD DE CHUNKS' as separador;

SELECT 
    'Mínima' as Estadística,
    MIN(LENGTH(string_value)) || ' caracteres' as Valor
FROM embedding_metadata WHERE key = 'chroma:document'
UNION ALL
SELECT 
    'Máxima',
    MAX(LENGTH(string_value)) || ' caracteres'
FROM embedding_metadata WHERE key = 'chroma:document'
UNION ALL
SELECT 
    'Promedio',
    ROUND(AVG(LENGTH(string_value)), 2) || ' caracteres'
FROM embedding_metadata WHERE key = 'chroma:document';

SELECT '';
SELECT '🔄 ANÁLISIS DE DUPLICACIÓN' as separador;

SELECT 
    'Total Chunks' as Métrica,
    CAST(COUNT(*) AS TEXT) as Valor
FROM embedding_metadata WHERE key = 'chroma:document'
UNION ALL
SELECT 
    'Chunks Únicos',
    CAST(COUNT(DISTINCT string_value) AS TEXT)
FROM embedding_metadata WHERE key = 'chroma:document'
UNION ALL
SELECT 
    'Duplicados',
    CAST(COUNT(*) - COUNT(DISTINCT string_value) AS TEXT)
FROM embedding_metadata WHERE key = 'chroma:document'
UNION ALL
SELECT 
    'Porcentaje Duplicación',
    ROUND((COUNT(*) - COUNT(DISTINCT string_value)) * 100.0 / COUNT(*), 2) || '%'
FROM embedding_metadata WHERE key = 'chroma:document';

SELECT '';
SELECT '⚠️  PROBLEMAS POTENCIALES' as separador;

SELECT 
    'Chunks Vacíos' as Problema,
    CAST(COUNT(*) AS TEXT) as Cantidad
FROM embedding_metadata 
WHERE key = 'chroma:document' AND (string_value IS NULL OR string_value = '')
UNION ALL
SELECT 
    'Chunks Muy Cortos (<100)',
    CAST(COUNT(*) AS TEXT)
FROM embedding_metadata 
WHERE key = 'chroma:document' AND LENGTH(string_value) < 100
UNION ALL
SELECT 
    'Chunks Muy Largos (>2000)',
    CAST(COUNT(*) AS TEXT)
FROM embedding_metadata 
WHERE key = 'chroma:document' AND LENGTH(string_value) > 2000;

SELECT '';
SELECT '✅ CALIDAD GENERAL' as separador;

WITH stats AS (
    SELECT 
        COUNT(*) as total,
        COUNT(DISTINCT string_value) as uniques,
        SUM(CASE WHEN LENGTH(string_value) < 100 THEN 1 ELSE 0 END) as shorts,
        SUM(CASE WHEN LENGTH(string_value) > 2000 THEN 1 ELSE 0 END) as longs
    FROM embedding_metadata 
    WHERE key = 'chroma:document'
)
SELECT 
    'Completitud' as Indicador,
    CASE WHEN total = uniques + (total - uniques) THEN '🟢 100%' ELSE '🔴 Incompleto' END as Estado
FROM stats
UNION ALL
SELECT 
    'Duplicación',
    CASE 
        WHEN (total - uniques) * 100.0 / total > 50 THEN '🔴 Alta (>' || ROUND((total - uniques) * 100.0 / total, 0) || '%)'
        WHEN (total - uniques) * 100.0 / total > 10 THEN '🟡 Media (' || ROUND((total - uniques) * 100.0 / total, 0) || '%)'
        ELSE '🟢 Baja (<10%)'
    END
FROM stats
UNION ALL
SELECT 
    'Chunks Problemáticos',
    CASE 
        WHEN (shorts + longs) * 100.0 / total > 20 THEN '🔴 ' || ROUND((shorts + longs) * 100.0 / total, 1) || '%'
        WHEN (shorts + longs) * 100.0 / total > 10 THEN '🟡 ' || ROUND((shorts + longs) * 100.0 / total, 1) || '%'
        ELSE '🟢 ' || ROUND((shorts + longs) * 100.0 / total, 1) || '%'
    END
FROM stats;

SELECT '';
SELECT '═══════════════════════════════════════════' as 'FIN DEL RESUMEN';
