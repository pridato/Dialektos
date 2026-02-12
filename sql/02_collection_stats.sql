-- ============================================================================
-- Script 2: Estadísticas de Colecciones
-- ============================================================================
-- Muestra información sobre las colecciones y su contenido

.headers on
.mode column
.width 20 40 15

SELECT '=== INFORMACIÓN DE COLECCIONES ===' as info;

-- Detalles de cada colección
SELECT 
    name as coleccion,
    id as collection_id,
    topic as tema,
    dimension as dimensiones_embedding,
    database_id
FROM collections;

-- Conteo de documentos por colección
SELECT '' as separador;
SELECT '=== DOCUMENTOS POR COLECCIÓN ===' as info;

SELECT 
    COUNT(*) as total_embeddings
FROM embeddings;

-- Información sobre segmentos
SELECT '' as separador;
SELECT '=== SEGMENTOS DE LA COLECCIÓN ===' as info;

SELECT 
    type as tipo,
    scope as alcance,
    topic as tema
FROM segments
LIMIT 10;
