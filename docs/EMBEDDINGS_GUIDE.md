# Guía del Sistema de Vectorización

## 📚 Descripción

Sistema de vectorización implementado con **Sentence Transformers** y **ChromaDB** para el proyecto Dialektos. Convierte texto en vectores de alta calidad para búsqueda semántica.

## 🎯 Características Implementadas

### ✅ Modelos de Embeddings Configurables
- Soporte para múltiples modelos de Sentence Transformers
- Modelo recomendado: `paraphrase-multilingual-mpnet-base-v2`
  - 768 dimensiones
  - Optimizado para español e inglés
  - Balance ideal calidad/velocidad

### ✅ Búsqueda Semántica Avanzada
- **semantic_search()**: Búsqueda básica con scores de similitud
- **search_with_filters()**: Filtrado por metadata (carpeta, archivo, página)
- **get_similar_chunks()**: Encontrar contenido relacionado
- **get_collection_stats()**: Estadísticas de la colección

### ✅ Persistencia Local
- ChromaDB almacena embeddings en disco (`data/chroma_db/`)
- No requiere servidor externo
- Funciona offline después de descargar el modelo

## 🚀 Instalación

### 1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

Esto instalará:
- `sentence-transformers==2.5.1`
- `torch>=2.0.0`
- `chromadb==0.4.22`

### 2. Primera Descarga del Modelo

El modelo se descarga automáticamente en la primera ejecución:
- Tamaño: ~420MB
- Ubicación: `~/.cache/huggingface/`
- Solo se descarga una vez

## 📖 Uso

### Opción 1: Re-vectorizar desde Cero

Si quieres usar el nuevo modelo de embeddings:

```bash
python src/ingest/pdf_extractor.py
```

**IMPORTANTE**: Si ya tienes una base de datos ChromaDB existente con otro modelo, debes:

1. Editar `src/ingest/pdf_extractor.py`
2. Descomentar la línea: `db.reset_collection()`
3. Ejecutar el script

### Opción 2: Demo Interactivo

Prueba todas las funcionalidades:

```bash
# Demo guiada (muestra 5 ejemplos)
python examples/demo_embeddings.py

# Modo interactivo (consultas personalizadas)
python examples/demo_embeddings.py --interactive
```

### Opción 3: Uso Programático

```python
from src.ingest.pdf_extractor import ChromaDBPersistence

# Inicializar con modelo personalizado
db = ChromaDBPersistence(
    model_name="paraphrase-multilingual-mpnet-base-v2",
    persist_directory="data/chroma_db"
)

# Búsqueda semántica básica
results = db.semantic_search(
    query="¿Qué es álgebra lineal?",
    n_results=5
)

for result in results:
    print(f"Score: {result['score']:.3f}")
    print(f"Texto: {result['text'][:100]}...")
    print(f"Archivo: {result['metadata']['filename']}\n")

# Búsqueda con filtros
results = db.search_with_filters(
    query="matrices y vectores",
    filters={"source_folder": "Algebra"},
    n_results=3
)

# Estadísticas
stats = db.get_collection_stats()
print(f"Total chunks: {stats['total_chunks']}")
print(f"Archivos: {stats['unique_files']}")
```

## 🔧 Configuración de Modelos

### Modelos Disponibles

Ver todos los modelos configurados:

```python
from src.ingest import embeddings_config

# Listar modelos multilingües
multilingual = embeddings_config.list_available_models(
    language=embeddings_config.Language.MULTILINGUAL
)

# Ver información de un modelo
embeddings_config.print_model_info("paraphrase-multilingual-mpnet-base-v2")

# Comparar modelos
embeddings_config.compare_models([
    "paraphrase-multilingual-mpnet-base-v2",
    "all-MiniLM-L6-v2"
])
```

### Modelos Recomendados

| Modelo | Dimensión | Tamaño | Velocidad | Calidad | Uso |
|--------|-----------|---------|-----------|---------|-----|
| **paraphrase-multilingual-mpnet-base-v2** | 768 | 420MB | Media | Alta | **Recomendado para Dialektos** |
| paraphrase-multilingual-MiniLM-L12-v2 | 384 | 120MB | Rápida | Media | Prototipado rápido |
| all-mpnet-base-v2 | 768 | 420MB | Media | Muy Alta | Solo inglés |
| all-MiniLM-L6-v2 | 384 | 80MB | Muy Rápida | Baja | Testing |

## 📊 Interpretación de Scores

Los scores de similitud van de 0 a 1:

- **0.8 - 1.0**: Muy relevante (excelente para RAG)
- **0.6 - 0.8**: Relevante (aceptable)
- **0.4 - 0.6**: Poco relevante (usar con precaución)
- **0.0 - 0.4**: Irrelevante (descartar)

**Recomendación para RAG**: Usar umbral mínimo de 0.7

```python
# Filtrar por score mínimo
results = db.semantic_search(
    query="tu consulta",
    n_results=10,
    min_similarity=0.7  # Solo resultados con score >= 0.7
)
```

## 🎯 Casos de Uso

### 1. Búsqueda Semántica Simple

```python
results = db.semantic_search("¿Qué es una matriz?", n_results=3)
```

### 2. Búsqueda por Asignatura

```python
results = db.search_with_filters(
    query="derivadas e integrales",
    filters={"source_folder": "Calculo"},
    n_results=5
)
```

### 3. Exploración de Contenido Relacionado

```python
# Obtener un chunk
results = db.semantic_search("vectores", n_results=1)
chunk_id = results[0]['chunk_id']

# Encontrar chunks similares
similar = db.get_similar_chunks(chunk_id, n_results=5)
```

### 4. Análisis de Cobertura

```python
stats = db.get_collection_stats()
print(f"Documentos indexados: {stats['unique_files']}")
print(f"Carpetas: {', '.join(stats['unique_folders'])}")
```

## 🔄 Re-vectorización

### ¿Cuándo re-vectorizar?

- Cambias el modelo de embeddings
- Añades nuevos PDFs
- Actualizas el contenido existente

### Proceso

1. **Backup** (opcional): Copia `data/chroma_db/` a otro lugar

2. **Reiniciar colección**:
   ```python
   db = ChromaDBPersistence()
   db.reset_collection()  # ⚠️ Elimina todos los datos
   ```

3. **Re-vectorizar**:
   ```bash
   python src/ingest/pdf_extractor.py
   ```

### Tiempo Estimado

- 100 chunks: ~30 segundos
- 500 chunks: ~2 minutos
- 1000 chunks: ~5 minutos

(Primera ejecución: +1 minuto para descargar el modelo)

## 🐛 Troubleshooting

### Error: "chromadb not installed"
```bash
pip install chromadb
```

### Error: "sentence-transformers not installed"
```bash
pip install sentence-transformers torch
```

### Error: "No chunks in database"
```bash
# Primero procesa los PDFs
python src/ingest/pdf_extractor.py
```

### Warning: Modelo diferente al esperado

Si ves este warning:
```
⚠️ La colección usa el modelo 'X' pero especificaste 'Y'
```

Solución:
1. Resetear la colección: `db.reset_collection()`
2. Re-vectorizar con el nuevo modelo

## 📈 Performance

### Benchmarks (MacBook Pro M1, 16GB RAM)

| Operación | Tiempo | Notas |
|-----------|--------|-------|
| Carga inicial de modelo | ~3s | Solo primera vez por sesión |
| Vectorización (100 chunks) | ~30s | Depende del tamaño de texto |
| Búsqueda (1000 chunks) | <100ms | Muy rápido gracias a HNSW |
| Búsqueda filtrada | <150ms | Similar a búsqueda normal |

### Optimizaciones

- ChromaDB usa HNSW para búsqueda aproximada (muy rápida)
- Embeddings se cachean en disco (no se recalculan)
- Modelo se carga una vez por sesión

## 🔗 Integración con LLM (Módulo 2)

El sistema está listo para integrarse con el retrieval system:

```python
def retrieve_context(query: str, n_results: int = 3) -> List[str]:
    """Obtiene contexto relevante para el LLM."""
    db = ChromaDBPersistence()
    
    results = db.semantic_search(
        query=query,
        n_results=n_results,
        min_similarity=0.7
    )
    
    # Extraer solo el texto para el LLM
    contexts = [r['text'] for r in results]
    
    return contexts

# Uso con LLM
user_query = "¿Qué es una matriz?"
context = retrieve_context(user_query)
prompt = f"Contexto:\n{' '.join(context)}\n\nPregunta: {user_query}"
# Enviar prompt al LLM...
```

## 📝 Próximos Pasos

1. ✅ Vectorización implementada
2. ⏳ **Siguiente**: Retrieval System (Módulo 2)
3. ⏳ Metadatos estructurados (asignatura, tipo, fecha)
4. ⏳ Integración con LLM

## 🤝 Contribuciones

Configuración centralizada en: `src/ingest/embeddings_config.py`

Para añadir un nuevo modelo:

```python
AVAILABLE_MODELS["nuevo-modelo"] = EmbeddingModelConfig(
    name="nuevo-modelo",
    dimension=768,
    size_mb=400,
    quality=EmbeddingQuality.BALANCED,
    languages=[Language.MULTILINGUAL],
    description="Descripción del modelo",
    recommended_for=["Casos de uso"]
)
```

---

**Última actualización**: 2026-02-12  
**Autor**: David Arroyo  
**Proyecto**: Dialektos - Sistema RAG Adaptativo
