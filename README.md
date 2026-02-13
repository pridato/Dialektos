# Dialektos

Sistema RAG (Retrieval-Augmented Generation) adaptativo para aprendizaje personalizado en Ciencia de Datos e Inteligencia Artificial, con motor de bio-adaptabilidad basado en datos fisiológicos (Suunto) y un Índice Cognitivo Diario (ICD).

## Descripción

**Dialektos** es un asistente de estudio inteligente que combina:

1. **Búsqueda semántica vectorial** sobre tus apuntes (PDFs) con modelos de lenguaje (GPT-4o).
2. **Motor de bio-adaptabilidad** que calcula un Índice Cognitivo Diario (ICD) a partir de biométricas de Suunto (HRV, sueño, body resources) y autoevaluación subjetiva, y adapta la dificultad del estudio en consecuencia.
3. **Modo Adversario (Socrático)** que cuestiona tus respuestas en vez de dártelas directamente.

### Características Principales

- **Vectorización Multilingüe**: Embeddings optimizados para español e inglés (Sentence Transformers, `paraphrase-multilingual-mpnet-base-v2`).
- **Búsqueda Semántica con Filtros**: ChromaDB con filtros por metadata (asignatura, archivo, página).
- **Router de Búsqueda**: Si la similitud en ChromaDB < 0.7, activa búsqueda web (Tavily) automáticamente.
- **Modo Socrático**: Prompt engineering para que la IA te interrogue en vez de dar respuestas directas.
- **Índice Cognitivo Diario (ICD)**: Score 0-100 que pondera HRV, sueño, body resources, energía y claridad mental.
- **Motor de Decisión Pedagógica**: Mapea el ICD a estrategias de estudio (Deep Work, Flow, Review, Survival).
- **Ingesta de Suunto**: Parser de JSON exportado desde la Suunto App.
- **Persistencia Local**: SQLite para biométricas, ChromaDB para vectores. Sin servidor externo.

## Arquitectura

```
Dialektos/
├── src/
│   ├── ingest/                    # Pipeline de ingesta de PDFs
│   │   ├── pdf_reader.py          # Extracción de texto de PDFs
│   │   ├── chroma_persistence.py  # Gestión de ChromaDB y búsqueda semántica
│   │   ├── text_cleaner.py        # Limpieza de texto
│   │   ├── metadata_extractor.py  # Extracción de metadata estructurada
│   │   ├── models.py              # Modelos Pydantic (DocumentChunk, etc.)
│   │   └── embeddings_config.py   # Configuración de embeddings
│   ├── brain/                     # Lógica RAG y razonamiento
│   │   ├── retriever.py           # Flujo RAG: búsqueda → prompt → LLM
│   │   ├── llm_client.py          # Cliente OpenAI (GPT-4o mini)
│   │   ├── memory.py              # Memoria conversacional multi-turno
│   │   ├── adversary.py           # Modo socrático / adversario
│   │   ├── web_search.py          # Búsqueda web Tavily (fallback)
│   │   └── user_profile.py        # Perfil de usuario para system prompt
│   └── bio/                       # Motor de bio-adaptabilidad
│       ├── models.py              # SQLModel: DailyBiometrics, StudySession, DailyConfounders
│       ├── db.py                  # Engine SQLite (data/metrics.db)
│       ├── dao.py                 # CRUD con cálculo automático de métricas derivadas
│       ├── metrics.py             # Feature engineering: ln_rmssd, EMA, ICD
│       ├── decision.py            # ICD → zona cognitiva → estrategia pedagógica
│       ├── test_metrics.py        # Tests de métricas derivadas
│       └── test_decision.py       # Tests del motor de decisión (25 tests)
├── scripts/
│   ├── ingest_suunto_json.py      # Ingesta de datos Suunto vía DAO
│   ├── ingest_suunto_data.py      # Ingesta alternativa
│   └── ingest_json_simple.py      # Ingesta manual sin DAO
├── notebooks/
│   ├── icd_dashboard.ipynb        # Dashboard visual del ICD
│   └── tarea_3.3_ln_rmssd_estudio.ipynb  # Estudio de normalización HRV
├── config/
│   ├── user_profile.json          # Identidad, objetivos, preferencias
│   └── metadata_config.yaml       # Metadata de PDFs por asignatura
├── data/
│   ├── raw_pdfs/                  # PDFs originales
│   ├── processed/                 # Textos extraídos y chunks (JSON)
│   ├── chroma_db/                 # Base de datos vectorial ChromaDB
│   ├── biometrics/                # Exportaciones JSON de Suunto
│   └── metrics.db                 # SQLite con biométricas y sesiones (runtime)
├── docs/                          # Documentación técnica
│   ├── TAREAS.md                  # Roadmap detallado del proyecto
│   ├── EMBEDDINGS_GUIDE.md        # Guía del sistema de vectorización
│   └── RESUMEN_TAREAS_3_3.4.md    # Resumen de tareas de bio-adaptabilidad
├── sql/                           # Scripts de análisis SQL sobre ChromaDB
└── logs/                          # Logs de procesamiento
```

## Flujos de Datos

### Flujo RAG (Pregunta → Respuesta)

```
Pregunta del usuario
    → Query rewriting (si hay historial multi-turno)
    → Búsqueda semántica en ChromaDB
    → Si similitud ≥ 0.7: usar apuntes
      Si similitud < 0.7: búsqueda web (Tavily)
    → Construir prompt con perfil de usuario + contexto
    → LLM (GPT-4o mini) → Respuesta
```

### Flujo Bio-Adaptabilidad (Suunto → Estrategia)

```
Exportación Suunto (JSON)
    → Parser → DailyBiometrics + datos subjetivos
    → compute_derived_metrics:
        • ln_rmssd = ln(hrv_rmssd)
        • hrv_baseline_7d = EMA(ln_rmssd, span=7)
        • sleep_consistency = std(hora_dormir, 7 días)
        • icd_score = ponderación de Z-scores y normalizaciones
    → Guardar en metrics.db
    → classify_zone(icd_score) → CognitiveZone
    → get_strategy(zone) → PedagogicalStrategy
        • ICD > 80: Deep Work (temas nuevos, socrático)
        • ICD 50-80: Flow (práctica, ejercicios)
        • ICD 30-50: Review (repaso espaciado)
        • ICD < 30: Survival (solo contenido pasivo)
```

## Instalación

### Requisitos Previos

- Python 3.11+
- 4 GB de RAM mínimo (recomendado 8 GB)
- ~500 MB de espacio para el modelo de embeddings

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

**Nota:** En la primera ejecución, el modelo de Sentence Transformers (~420 MB) se descarga automáticamente en `~/.cache/huggingface/`.

### 4. Configurar Variables de Entorno

```bash
cp .env.example .env
# Edita .env con tus API keys
```

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `OPENAI_API_KEY` | Sí | Para GPT-4o mini. Obtén en [OpenAI](https://platform.openai.com/api-keys) |
| `TAVILY_API_KEY` | No | Para búsqueda web cuando similitud ChromaDB < 0.7. Obtén en [Tavily](https://app.tavily.com) |

## Uso

### Pipeline RAG: Procesamiento de PDFs

Coloca tus PDFs en `data/raw_pdfs/` y ejecuta:

```bash
python src/ingest/pdf_reader.py
```

Esto realiza: extracción de texto, limpieza, chunking inteligente (sin cortar frases), generación de embeddings y almacenamiento en ChromaDB.

### Búsqueda Semántica

```python
from src.ingest.chroma_persistence import ChromaDBPersistence

db = ChromaDBPersistence(
    model_name="paraphrase-multilingual-mpnet-base-v2",
    persist_directory="data/chroma_db"
)

# Búsqueda básica
results = db.semantic_search(query="¿Qué es regresión lineal?", n_results=5)

# Búsqueda con filtro por asignatura
results = db.search_with_filters(
    query="matrices y vectores",
    filters={"source_folder": "AlgebraLineal"},
    n_results=3
)
```

### Ingesta de Datos Biométricos (Suunto)

Coloca tu exportación JSON de Suunto en `data/biometrics/` y ejecuta:

```bash
python scripts/ingest_suunto_json.py
```

Esto parsea los datos de HRV, sueño y body resources, calcula las métricas derivadas (`ln_rmssd`, `hrv_baseline_7d`, `sleep_consistency`, `icd_score`) y los almacena en `data/metrics.db`.

### Consultar el ICD del Día

```python
from src.bio.db import get_engine
from src.bio.models import DailyBiometrics
from sqlmodel import Session, select
from datetime import date

engine = get_engine()
with Session(engine) as session:
    today = session.exec(
        select(DailyBiometrics).where(DailyBiometrics.date == date.today())
    ).first()
    if today:
        print(f"ICD: {today.icd_score:.1f}/100")
```

### Motor de Decisión Pedagógica

```python
from src.bio.decision import classify_zone, get_strategy

zone = classify_zone(icd_score=72.5)
strategy = get_strategy(zone)

print(f"Zona: {zone.value}")         # "normal"
print(f"Modo IA: {strategy.ai_mode}") # "guided"
print(f"Tareas: {strategy.tasks}")     # ["coding", "standard_exercises"]
```

## Modelo de Datos (Bio-Adaptabilidad)

Esquema Star Schema en SQLite (`data/metrics.db`):

| Tabla | Tipo | Descripción |
|-------|------|-------------|
| `DailyBiometrics` | Hechos (PK: date) | Datos objetivos Suunto + subjetivos + métricas derivadas |
| `StudySession` | Dimensión (FK: date) | Sesiones de estudio (múltiples por día) — variable objetivo Y |
| `DailyConfounders` | Dimensión (FK: date, 1:1) | Variables de confusión (cafeína, pantalla, estrés, ejercicio) |

### Fórmula ICD

```
ICD = 0.25·Z(ln_rmssd) + 0.20·Z(sleep_quality) + 0.20·body_resources_norm
    + 0.15·energy_norm + 0.10·mental_clarity_norm + 0.10·mood_bonus
```

Los pesos son hipótesis iniciales que se recalibrarán con regresión lineal tras acumular 30-60 días de datos.

## Tecnologías

### Core RAG
- **LangChain** (0.1.9) — Framework para aplicaciones LLM
- **ChromaDB** (≥0.5.0) — Base de datos vectorial
- **Sentence Transformers** (2.5.1) — Embeddings multilingües
- **OpenAI** (≥2.20.0) — GPT-4o mini
- **Tavily** (0.3.3) — Búsqueda web (fallback del router)

### Bio-Adaptabilidad
- **SQLModel** (≥0.0.14) — ORM para metrics.db
- **NumPy** (1.26.4) — Operaciones numéricas (EMA, Z-scores)
- **Pandas** (2.2.0) — Análisis y manipulación de datos

### Procesamiento de Documentos
- **PyPDF** (4.0.1) — Extracción de texto de PDFs
- **tiktoken** (0.6.0) — Tokenización
- **PyYAML** (≥6.0) — Configuración de metadata

### UI y Visualización
- **Streamlit** (1.31.1) — Interfaz de usuario (planificado)
- **Plotly** (5.19.0) — Visualizaciones interactivas
- **Matplotlib** (3.8.3) — Gráficos estáticos
- **Seaborn** (0.13.2) — Visualización estadística

## Roadmap

### Completado

- [x] **Módulo 1 — Data Pipeline**: Extracción de PDFs, chunking, vectorización, ChromaDB, metadata
- [x] **Módulo 2 — Core Logic**: Conexión LLM, retrieval, perfil de usuario, modo socrático, router web
- [x] **Módulo 3.1** — Modelado de datos: `DailyBiometrics`, `StudySession`, `DailyConfounders`
- [x] **Módulo 3.2** — Ingesta de datos Suunto (parser JSON)
- [x] **Módulo 3.3** — Feature engineering: `ln_rmssd`, `hrv_baseline_7d`, `sleep_consistency`
- [x] **Módulo 3.4** — Algoritmo ICD (`calculate_icd`)
- [x] **Módulo 3.5** — Motor de decisión: ICD → zona cognitiva → estrategia pedagógica

### En Desarrollo

- [ ] **Módulo 3.6** — Sistema de registro post-sesión (formulario `StudySession`)
- [ ] **Módulo 3.7** — Análisis de correlación semanal (HRV vs. rendimiento, confounders)

### Planificado

- [ ] **Módulo 4** — Interfaz Streamlit completa:
  - Chat adaptativo con modo según ICD
  - Dashboard ICD en tiempo real
  - Tracking de sesiones de estudio
  - Dashboard de correlación HRV-Rendimiento
- [ ] **Módulo 5** — DevOps: gestión de secretos, refactorización modular

Ver [TAREAS.md](docs/TAREAS.md) para el roadmap detallado con niveles de dificultad.

## Tests

```bash
# Tests del motor de decisión (25 tests)
pytest src/bio/test_decision.py -v

# Verificación de métricas derivadas
python src/bio/test_metrics.py
```

## Documentación Adicional

- [**Guía de Embeddings**](docs/EMBEDDINGS_GUIDE.md) — Sistema de vectorización completo
- [**Tareas del Proyecto**](docs/TAREAS.md) — Roadmap detallado por módulos
- [**Resumen Bio-Adaptabilidad**](docs/RESUMEN_TAREAS_3_3.4.md) — Tareas 3.3 y 3.4
- [**SQL README**](sql/README.md) — Análisis y consultas SQL sobre ChromaDB

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'sentence_transformers'`

```bash
pip install sentence-transformers torch
```

### Error: `ChromaDB collection already exists with different embedding dimension`

```python
db.reset_collection()  # Resetear y re-vectorizar
```

### PDFs no se procesan correctamente

- Verifica que los PDFs no estén protegidos con contraseña
- PDFs escaneados requieren OCR (no implementado)
- Revisa `logs/pdf_extraction.log`

## Autor

**David Arroyo**
- Proyecto: Sistema RAG Adaptativo para Aprendizaje en Data Science
- Contexto: Universidad, especialización en Ciencia de Datos e IA

## Licencia

Proyecto de código abierto para fines educativos.

---

*Proyecto en desarrollo activo. Última actualización: febrero 2026.*
