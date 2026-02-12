# 📊 Scripts SQL para Análisis de ChromaDB - Dialektos

Esta carpeta contiene scripts SQL para inspeccionar y analizar los chunks y embeddings almacenados en ChromaDB.

## 🎯 Descripción de Scripts

### 01_inspect_schema.sql
**Propósito**: Inspeccionar la estructura completa de la base de datos
- Muestra todas las tablas disponibles
- Describe la estructura de cada tabla
- Lista todos los índices creados

### 02_collection_stats.sql
**Propósito**: Estadísticas generales de colecciones
- Información de colecciones configuradas
- Conteo de documentos por colección
- Distribución de segmentos

### 03_chunks_analysis.sql
**Propósito**: Análisis detallado de chunks
- Resumen general (total chunks, longitudes, etc.)
- Distribución de chunks por documento
- Análisis de metadatos
- Muestra de chunks almacenados

### 04_embeddings_quality.sql
**Propósito**: Validación de calidad de embeddings
- Verificación de completitud de embeddings
- Análisis de consistencia en tamaños
- Detección de chunks problemáticos
- Análisis de duplicación

### 05_search_examples.sql
**Propósito**: Ejemplos de búsqueda y filtrado
- Búsqueda por términos específicos
- Distribución por longitud de texto
- Exploración de metadatos

## 🚀 Cómo Ejecutar

### Opción 1: Ejecutar un script individual
```bash
sqlite3 data/chroma_db/chroma.sqlite3 < sql/01_inspect_schema.sql
```

### Opción 2: Ejecutar todos los scripts secuencialmente
```bash
./sql/run_all_queries.sh
```

### Opción 3: Modo interactivo
```bash
sqlite3 data/chroma_db/chroma.sqlite3
sqlite> .read sql/01_inspect_schema.sql
```

### Opción 4: Generar reporte completo
```bash
python sql/generate_report.py
```

## 📋 Salida Esperada

Cada script genera:
- Tablas formateadas con estadísticas
- Indicadores de calidad de datos
- Muestras representativas de chunks
- Métricas de rendimiento

## 🔍 Análisis Recomendado

1. **Primero**: `01_inspect_schema.sql` - Entender la estructura
2. **Segundo**: `02_collection_stats.sql` - Ver el volumen de datos
3. **Tercero**: `03_chunks_analysis.sql` - Analizar distribución
4. **Cuarto**: `04_embeddings_quality.sql` - Validar calidad
5. **Quinto**: `05_search_examples.sql` - Probar búsquedas

## 📊 Métricas Clave

### Indicadores de Salud
- ✅ **Completitud**: 100% de embeddings generados
- ✅ **Consistencia**: Tamaño uniforme de embeddings
- ⚠️ **Duplicación**: <5% es aceptable
- ✅ **Longitud**: Chunks entre 100-1000 caracteres

### Alertas
- ❌ Chunks vacíos o muy cortos (<50 chars)
- ❌ Chunks excesivamente largos (>2000 chars)
- ❌ Alta duplicación (>10%)
- ❌ Embeddings faltantes

## 🛠️ Requisitos

- SQLite3 instalado
- Base de datos ChromaDB en `data/chroma_db/chroma.sqlite3`
- Python 3.8+ (para el generador de reportes)

## 📖 Notas Técnicas

### Estructura de ChromaDB
ChromaDB usa SQLite internamente con las siguientes tablas principales:
- `collections`: Colecciones de documentos
- `embeddings`: Vectores y documentos
- `segments`: Índices HNSW para búsqueda
- `metadata`: Información adicional

### Modelo de Embeddings
- **Modelo**: paraphrase-multilingual-mpnet-base-v2
- **Dimensiones**: 768 (típicamente)
- **Tipo**: Sentence Transformers
- **Idioma**: Multilingüe (optimizado para español)

---

**Proyecto**: Dialektos - Sistema RAG Adaptativo  
**Autor**: David Arroyo  
**Última actualización**: Febrero 2026
