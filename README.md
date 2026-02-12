# Dialektos

Sistema RAG (Retrieval-Augmented Generation) adaptativo para aprendizaje personalizado en Ciencia de Datos e Inteligencia Artificial.

## 📖 Descripción

**Dialektos** es un asistente de estudio inteligente que combina búsqueda semántica vectorial con modelos de lenguaje para crear una experiencia de aprendizaje adaptativa. El sistema procesa documentos PDF de tus asignaturas, los vectoriza usando embeddings multilingües y proporciona respuestas contextualizadas basadas en tu material de estudio.

### Características Principales

- ✅ **Vectorización Multilingüe**: Embeddings optimizados para español e inglés usando Sentence Transformers
- ✅ **Búsqueda Semántica Avanzada**: ChromaDB con filtros por metadata (asignatura, archivo, página)
- ✅ **Procesamiento Inteligente de PDFs**: Extracción, limpieza y chunking optimizado de documentos
- ✅ **Persistencia Local**: Base de datos vectorial en disco, sin servidor externo necesario
- 🚧 **Sistema Adaptativo**: Motor de decisión basado en estado físico y cognitivo (en desarrollo)
- 🚧 **Router Inteligente**: Combina búsqueda en apuntes con búsqueda web según relevancia (planificado)

## 🏗️ Arquitectura

```
Dialektos/
├── src/
│   └── ingest/              # Pipeline de ingesta de datos
│       ├── pdf_reader.py    # Lectura básica de PDFs
│       ├── pdf_extractor.py # Extracción y chunking
│       ├── models.py        # Modelos de datos (DocumentChunk)
│       ├── chroma_persistence.py  # Gestión de ChromaDB
│       ├── text_cleaner.py  # Limpieza de texto
│       └── embeddings_config.py   # Configuración de embeddings
├── data/
│   ├── raw_pdfs/            # PDFs originales
│   ├── processed/           # Textos extraídos y chunks
│   └── chroma_db/           # Base de datos vectorial
├── sql/                     # Scripts de análisis SQL sobre ChromaDB
├── docs/                    # Documentación técnica
│   ├── EMBEDDINGS_GUIDE.md  # Guía del sistema de vectorización
│   └── TAREAS.md            # Roadmap del proyecto
└── logs/                    # Logs de procesamiento
```

## 🚀 Instalación

### Requisitos Previos

- Python 3.11+
- 4GB de RAM mínimo (recomendado 8GB para procesamiento de PDFs grandes)
- ~500MB de espacio en disco para el modelo de embeddings

### 1. Clonar el Repositorio

```bash
git clone <repository-url>
cd Dialektos
```

### 2. Crear Entorno Virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

**Nota:** En la primera ejecución, el modelo de Sentence Transformers (~420MB) se descargará automáticamente en `~/.cache/huggingface/`.

### 4. Configurar Variables de Entorno (Opcional)

Si planeas usar integraciones con LLMs:

```bash
cp .env.example .env
# Edita .env con tus API keys
```

## 📚 Uso

### Procesamiento de PDFs

Coloca tus PDFs en `data/raw_pdfs/` y ejecuta:

```bash
python src/ingest/pdf_extractor.py
```

Esto realizará:
1. Extracción de texto de todos los PDFs
2. Limpieza y normalización
3. Chunking inteligente (sin cortar frases a la mitad)
4. Generación de embeddings
5. Almacenamiento en ChromaDB

### Búsqueda Semántica

```python
from src.ingest.chroma_persistence import ChromaDBPersistence

# Inicializar base de datos
db = ChromaDBPersistence(
    model_name="paraphrase-multilingual-mpnet-base-v2",
    persist_directory="data/chroma_db"
)

# Búsqueda básica
results = db.semantic_search(
    query="¿Qué es regresión lineal?",
    n_results=5
)

for result in results:
    print(f"Score: {result['score']:.3f}")
    print(f"Texto: {result['text'][:150]}...")
    print(f"Fuente: {result['metadata']['filename']}\n")
```

### Búsqueda con Filtros

```python
# Filtrar por asignatura
results = db.search_with_filters(
    query="matrices y vectores",
    filters={"source_folder": "AlgebraLineal"},
    n_results=3
)

# Filtrar por archivo específico
results = db.search_with_filters(
    query="teorema del límite central",
    filters={"filename": "Estadistica.pdf"},
    n_results=5
)
```

### Estadísticas de la Colección

```python
stats = db.get_collection_stats()
print(f"Total chunks: {stats['total_documents']}")
print(f"Archivos indexados: {stats['unique_files']}")
```

## 🔬 Análisis y Mantenimiento

### Análisis SQL

El directorio `sql/` contiene scripts para análisis avanzado de la base de datos:

```bash
# Inspeccionar esquema
sqlite3 data/chroma_db/chroma.sqlite3 < sql/01_inspect_schema.sql

# Estadísticas de colección
sqlite3 data/chroma_db/chroma.sqlite3 < sql/02_collection_stats.sql

# Análisis de chunks
sqlite3 data/chroma_db/chroma.sqlite3 < sql/03_chunks_analysis.sql

# Generar reporte completo
python sql/generate_report.py
```

### Detección de Duplicados

```bash
python sql/detect_duplicates.py
python sql/cleanup_duplicates.py
```

## 📊 Tecnologías Utilizadas

### Core RAG
- **LangChain** (0.1.9): Framework para aplicaciones LLM
- **ChromaDB** (≥0.5.0): Base de datos vectorial
- **Sentence Transformers** (2.5.1): Generación de embeddings

### Procesamiento de Documentos
- **PyPDF** (4.0.1): Extracción de texto de PDFs
- **tiktoken** (0.6.0): Tokenización

### LLM & APIs
- **OpenAI** (1.12.0): Integración con GPT-4o
- **Tavily** (0.3.3): Búsqueda web para el router agent

### Data Science
- **NumPy** (1.26.4): Operaciones numéricas
- **Pandas** (2.2.0): Manipulación de datos
- **PyTorch** (≥2.0.0): Backend para Sentence Transformers

### UI & Visualización
- **Streamlit** (1.31.1): Framework de interfaz de usuario
- **Matplotlib** (3.8.3): Gráficos estáticos
- **Plotly** (5.19.0): Visualizaciones interactivas

## 🗺️ Roadmap

### ✅ Completado
- [x] Pipeline de extracción de PDFs
- [x] Chunking inteligente con RecursiveCharacterTextSplitter
- [x] Sistema de vectorización con Sentence Transformers
- [x] Persistencia local con ChromaDB
- [x] Búsqueda semántica con filtros de metadata
- [x] Scripts de análisis y limpieza SQL

### 🚧 En Desarrollo
- [ ] Conexión con LLM (GPT-4o)
- [ ] Sistema de retrieval con ranking de relevancia
- [ ] Prompt engineering para modo socrático
- [ ] Interfaz Streamlit básica

### 📋 Planificado
- [ ] Motor de adaptabilidad biológica (estado físico/cognitivo)
- [ ] Router inteligente (apuntes vs búsqueda web)
- [ ] Dashboard de métricas de aprendizaje
- [ ] Sistema de recomendación de temas
- [ ] Modo de streaming para respuestas

Ver [TAREAS.md](docs/TAREAS.md) para el roadmap detallado con niveles de dificultad.

## 📖 Documentación Adicional

- [**Guía de Embeddings**](docs/EMBEDDINGS_GUIDE.md): Documentación completa del sistema de vectorización
- [**SQL README**](sql/README.md): Guía de análisis y consultas SQL
- [**Tareas del Proyecto**](docs/TAREAS.md): Roadmap detallado por módulos

## 🔧 Modelo de Embeddings

Por defecto, Dialektos usa:

**Modelo:** `paraphrase-multilingual-mpnet-base-v2`
- **Dimensiones:** 768
- **Idiomas:** Español, Inglés (y 50+ más)
- **Rendimiento:** Balance óptimo entre calidad y velocidad
- **Tamaño:** ~420MB

### Cambiar Modelo

Para usar otro modelo de Sentence Transformers:

```python
db = ChromaDBPersistence(
    model_name="all-MiniLM-L6-v2",  # Más rápido pero solo inglés
    persist_directory="data/chroma_db"
)
```

**Importante:** Si cambias de modelo, debes re-vectorizar toda la base de datos:

```python
db.reset_collection()  # Limpia la colección existente
# Luego re-ejecuta el pipeline de ingesta
```

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'sentence_transformers'"

```bash
pip install sentence-transformers torch
```

### Error: "ChromaDB collection already exists with different embedding dimension"

Estás intentando usar un modelo diferente en una colección existente:

```python
# Opción 1: Resetear la colección
db.reset_collection()

# Opción 2: Usar un nombre diferente de colección
db = ChromaDBPersistence(collection_name="dialektos_v2")
```

### PDFs no se procesan correctamente

- Verifica que los PDFs no estén protegidos con contraseña
- Algunos PDFs escaneados requieren OCR (no implementado aún)
- Revisa `logs/pdf_extraction.log` para detalles

## 👤 Autor

**David Arroyo**
- Proyecto: Sistema RAG Adaptativo para Aprendizaje en Data Science
- Contexto: Universidad, especialización en Ciencia de Datos e IA

## 📄 Licencia

Este proyecto es de código abierto para fines educativos.

## 🙏 Agradecimientos

- **LangChain** por el framework RAG
- **ChromaDB** por la base de datos vectorial eficiente
- **Sentence Transformers** por los modelos de embeddings multilingües
- **Hugging Face** por el ecosistema de ML/NLP

---

**Nota:** Este proyecto está en desarrollo activo. Las funcionalidades pueden cambiar según las necesidades del roadmap académico.
