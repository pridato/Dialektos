-- ============================================================================
-- Script 1: Inspección del Esquema de ChromaDB
-- ============================================================================
-- Este script muestra la estructura de tablas en la base de datos ChromaDB

-- Mostrar todas las tablas disponibles
.headers on
.mode column

SELECT '=== TABLAS EN LA BASE DE DATOS ===' as info;
SELECT name as tabla_name, type 
FROM sqlite_master 
WHERE type='table'
ORDER BY name;

-- Estructura de la tabla de colecciones
SELECT '' as separador;
SELECT '=== ESTRUCTURA: collections ===' as info;
PRAGMA table_info(collections);

-- Estructura de la tabla de embeddings
SELECT '' as separador;
SELECT '=== ESTRUCTURA: embeddings ===' as info;
PRAGMA table_info(embeddings);

-- Estructura de la tabla de segmentos
SELECT '' as separador;
SELECT '=== ESTRUCTURA: segments ===' as info;
PRAGMA table_info(segments);

-- Ver todos los índices
SELECT '' as separador;
SELECT '=== ÍNDICES CREADOS ===' as info;
SELECT name, tbl_name, sql 
FROM sqlite_master 
WHERE type='index' 
ORDER BY tbl_name;
