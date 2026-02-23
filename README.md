# Dialektos

Sistema **RAG (Retrieval-Augmented Generation)** adaptativo para aprendizaje personalizado en Ciencia de Datos e IA, con motor de bio-adaptabilidad basado en biométricas (Suunto) y un **Índice Cognitivo Diario (ICD)** que adapta la dificultad del estudio a tu estado físico y mental.

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![Next.js](https://img.shields.io/badge/next.js-16.1.6-black)
![License](https://img.shields.io/badge/license-MIT-orange)

---

## 📋 Índice

- [Descripción](#-descripción)
- [Características principales](#-características-principales)
- [Arquitectura](#-arquitectura)
- [Flujos de datos](#-flujos-de-datos)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Modelo de datos (bio-adaptabilidad)](#-modelo-de-datos-bio-adaptabilidad)
- [Tecnologías](#-tecnologías)
- [Roadmap](#-roadmap)
- [Tests](#-tests)
- [Documentación](#-documentación)
- [Troubleshooting](#-troubleshooting)
- [Autor y licencia](#-autor-y-licencia)

---

## 🎯 Descripción

**Dialektos** es un asistente de estudio que combina tres pilares fundamentales:

| Pilar | Qué hace |
|-------|----------|
| **RAG sobre tus apuntes** | Búsqueda semántica vectorial sobre PDFs con GPT-4o. Respuestas basadas en tu material, no en conocimiento genérico. |
| **Bio-adaptabilidad** | Calcula un **ICD** (0–100) a partir de HRV, sueño y body resources (Suunto) + autoevaluación. Adapta estrategia de estudio según tu estado. |
| **Modo socrático** | La IA te cuestiona en lugar de dar la respuesta directa, para reforzar comprensión. |

Todo corre en local (ChromaDB, SQLite); solo las llamadas a OpenAI y opcionalmente Tavily usan servicios externos.

---

## ✨ Características principales

### 🧠 Sistema RAG
- **Vectorización multilingüe**: Embeddings español/inglés (`paraphrase-multilingual-mpnet-base-v2`)
- **Búsqueda semántica con filtros**: ChromaDB con metadata (asignatura, archivo, página)
- **Router de búsqueda**: Si similitud en ChromaDB < 0.7 → búsqueda web (Tavily) automática
- **Caché semántico**: Redis para evitar consultas repetidas al LLM
- **Memoria conversacional**: Persistencia de sesiones multi-turno en Redis

### 🎓 Motor Pedagógico
- **Modo socrático**: Prompts para que la IA interrogue en vez de explicar directamente
- **Mapa mental**: Generación de grafos de conceptos desde texto
- **Plan de estudio progresivo**: Rutas estructuradas con dependencias conceptuales
- **ICD**: Score 0–100 que combina HRV, sueño, body resources, energía y claridad mental
- **Estrategias adaptativas**: Deep Work, Flow, Review, Survival según tu ICD

### 📊 Bio-Tracker
- **Ingesta Suunto**: Parser de JSON exportado desde la Suunto App
- **Registro manual**: Entrada de datos biométricos y subjetivos
- **Visualización**: Dashboard con métricas y tendencias
- **Persistencia local**: SQLite para biométricas, ChromaDB para vectores

### 💻 Dashboard Next.js
- **Interfaz moderna**: UI responsive con Tailwind CSS y componentes Radix UI
- **Chat interactivo**: Interfaz tipo ChatGPT con streaming en tiempo real
- **Sesiones Focus**: HUD para registrar sesiones de estudio con métricas
- **Tema claro/oscuro**: Soporte completo para modo oscuro

---

## 🏗️ Arquitectura

```
Dialektos/
├── src/
│   ├── ingest/                    # Pipeline de ingesta de PDFs
│   │   ├── pdf_reader.py          # Extracción de texto
│   │   ├── chroma_persistence.py  # ChromaDB y búsqueda semántica
│   │   ├── text_cleaner.py        # Limpieza de texto
│   │   ├── metadata_extractor.py  # Metadata estructurada
│   │   ├── models.py              # Modelos Pydantic (DocumentChunk, etc.)
│   │   └── embeddings_config.py   # Configuración de embeddings
│   ├── brain/                     # Lógica RAG y razonamiento
│   │   ├── retriever.py           # Flujo RAG: búsqueda → prompt → LLM
│   │   ├── llm_client.py          # Cliente OpenAI (GPT-4o mini)
│   │   ├── memory.py              # Memoria conversacional multi-turno
│   │   ├── adversary.py            # Modo socrático / adversario
│   │   ├── web_search.py          # Búsqueda web Tavily (fallback)
│   │   ├── user_profile.py        # Perfil de usuario para system prompt
│   │   └── mindmapper.py          # Generación de mapas mentales y planes
│   ├── bio/                       # Motor de bio-adaptabilidad
│   │   ├── models.py              # SQLModel: DailyBiometrics, StudySession, DailyConfounders
│   │   ├── db.py                  # Engine SQLite (data/metrics.db)
│   │   ├── dao.py                 # CRUD y métricas derivadas
│   │   ├── metrics.py             # Feature engineering: ln_rmssd, EMA, ICD
│   │   ├── decision.py            # ICD → zona → estrategia pedagógica
│   │   ├── test_metrics.py        # Tests de métricas derivadas
│   │   └── test_decision.py       # Tests del motor de decisión (25 tests)
│   ├── cache/                     # Sistema de caché
│   │   ├── redis_client.py        # Cliente Redis
│   │   ├── rag_semantic_cache.py  # Caché semántico para RAG
│   │   └── session_memory.py      # Memoria de sesiones
│   └── utils/                     # Utilidades
│       └── cache.py               # Utilidades de caché
├── apps/
│   └── dashboard/                 # Dashboard Next.js
│       ├── app/                   # App Router de Next.js
│       │   ├── page.tsx           # Página principal
│       │   └── layout.tsx         # Layout principal
│       ├── components/            # Componentes React
│       │   ├── ui/                # Componentes UI base (shadcn/ui)
│       │   ├── theme-toggle.tsx   # Toggle de tema
│       │   ├── biometric-input-manual.tsx
│       │   ├── active-session-hud.tsx
│       │   ├── mind-map-view.tsx
│       │   └── markdown-renderer.tsx
│       ├── hooks/                 # Custom hooks
│       │   ├── use-icd.ts
│       │   ├── use-biometrics.ts
│       │   └── use-chat.ts
│       ├── lib/                   # Utilidades y tipos
│       │   ├── api.ts             # Cliente API
│       │   └── session-types.ts
│       └── api/                   # Backend FastAPI
│           └── main.py            # API REST
├── scripts/
│   ├── data/                      # Ingesta de datos
│   │   ├── ingest_suunto_json.py  # Ingesta Suunto vía DAO
│   │   ├── ingest_suunto_data.py  # Ingesta alternativa
│   │   └── ingest_json_simple.py  # Ingesta manual sin DAO
│   └── db/                        # Análisis y mantenimiento ChromaDB
│       ├── *.sql                 # Consultas y auditoría
│       ├── detect_duplicates.py  # Detección de duplicados
│       └── README.md             # Guía de uso
├── notebooks/
│   ├── icd_dashboard.ipynb        # Dashboard visual del ICD
│   └── tarea_3.3_ln_rmssd_estudio.ipynb
├── config/
│   ├── user_profile.json          # Identidad, objetivos, preferencias
│   └── metadata_config.yaml      # Metadata de PDFs por asignatura
├── data/
│   ├── raw_pdfs/                  # PDFs originales
│   ├── processed/                 # Textos y chunks (JSON)
│   ├── chroma_db/                 # Base de datos vectorial
│   ├── biometrics/                # Exportaciones JSON Suunto
│   └── metrics.db                 # SQLite biométricas (runtime)
├── docs/                          # Documentación técnica
├── tests/                         # Tests del proyecto
└── logs/                          # Logs de procesamiento
```

---

## 🔄 Flujos de datos

### Flujo RAG (pregunta → respuesta)

```
Pregunta del usuario
    → Query rewriting (si hay historial multi-turno)
    → Búsqueda semántica en ChromaDB
    → Si similitud ≥ 0.7: usar apuntes
      Si similitud < 0.7: búsqueda web (Tavily)
    → Construir prompt (perfil + contexto)
    → LLM (GPT-4o mini) → Respuesta (streaming)
    → Guardar en memoria de sesión (Redis)
```

### Flujo bio-adaptabilidad (Suunto → estrategia)

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
        • ICD > 80:  Deep Work (temas nuevos, socrático)
        • ICD 50–80: Flow (práctica, ejercicios)
        • ICD 30–50: Review (repaso espaciado)
        • ICD < 30:  Survival (solo contenido pasivo)
```

---

## 🚀 Instalación

### Requisitos

- **Python 3.11+**
- **Node.js 18+** (para el dashboard Next.js)
- **Redis** (para caché y sesiones)
- 4 GB RAM mínimo (recomendado 8 GB)
- ~500 MB para el modelo de embeddings (descarga automática en primera ejecución)

### Pasos

#### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd Dialektos
```

#### 2. Configurar backend Python

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
pip install -r apps/dashboard/api/requirements.txt
```

#### 3. Configurar frontend Next.js

```bash
cd apps/dashboard
npm install  # o pnpm install / yarn install
```

#### 4. Variables de entorno

Crear archivo `.env` en la raíz del proyecto:

```bash
cp .env.example .env
```

Editar `.env` con tus API keys:

```env
# OpenAI API Key (requerida)
OPENAI_API_KEY=sk-...

# Tavily API Key (opcional, para búsqueda web)
TAVILY_API_KEY=tvly-...

# Redis (opcional, para caché y sesiones)
REDIS_URL=redis://localhost:6379
```

#### 5. Inicializar base de datos

```bash
# Crear estructura de SQLite
python -c "from src.bio.db import get_engine; from src.bio.models import *; from sqlmodel import SQLModel; SQLModel.metadata.create_all(get_engine())"
```

#### 6. Iniciar servicios

**Terminal 1 - Backend FastAPI:**
```bash
cd apps/dashboard/api
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Frontend Next.js:**
```bash
cd apps/dashboard
npm run dev
```

**Terminal 3 - Redis (si no está corriendo):**
```bash
redis-server
```

El dashboard estará disponible en `http://localhost:3000` y la API en `http://localhost:8000`.

---

## 📖 Uso

### Inicio rápido

1. **Procesar PDFs**: Coloca PDFs en `data/raw_pdfs/` y ejecuta:
   ```bash
   python src/ingest/pdf_reader.py
   ```

2. **Ingesta Suunto** (opcional): Exportación JSON en `data/biometrics/`, luego:
   ```bash
   python scripts/data/ingest_suunto_json.py
   ```

3. **Abrir dashboard**: Navega a `http://localhost:3000` y usa las diferentes vistas:
   - **Chat Socrático**: Haz preguntas sobre tus apuntes
   - **Bio-Tracker**: Registra tus datos biométricos diarios
   - **Mapa mental**: Genera grafos de conceptos desde texto
   - **Sesión Focus**: Registra y analiza tus sesiones de estudio

### Búsqueda semántica (programática)

```python
from src.ingest.chroma_persistence import ChromaDBPersistence

db = ChromaDBPersistence(
    model_name="paraphrase-multilingual-mpnet-base-v2",
    persist_directory="data/chroma_db"
)

# Búsqueda básica
results = db.semantic_search(query="¿Qué es regresión lineal?", n_results=5)

# Con filtro por asignatura
results = db.search_with_filters(
    query="matrices y vectores",
    filters={"source_folder": "AlgebraLineal"},
    n_results=3
)
```

### Consultar el ICD del día

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

### Motor de decisión pedagógica

```python
from src.bio.decision import classify_zone, get_strategy

zone = classify_zone(icd_score=72.5)
strategy = get_strategy(zone)

print(f"Zona: {zone.value}")           # "normal"
print(f"Modo IA: {strategy.ai_mode}")  # "guided"
print(f"Tareas: {strategy.tasks}")      # ["coding", "standard_exercises"]
```

---

## 📊 Modelo de datos (bio-adaptabilidad)

Esquema tipo star en SQLite (`data/metrics.db`):

| Tabla | Tipo | Descripción |
|-------|------|-------------|
| `DailyBiometrics` | Hechos (PK: date) | Suunto + subjetivos + métricas derivadas |
| `StudySession` | Dimensión (FK: date) | Sesiones de estudio (variable objetivo Y) |
| `DailyConfounders` | Dimensión (FK: date, 1:1) | Confounders: cafeína, pantalla, estrés, ejercicio |

### Fórmula ICD

```
ICD = 0.25·Z(ln_rmssd) + 0.20·Z(sleep_quality) + 0.20·body_resources_norm
    + 0.15·energy_norm + 0.10·mental_clarity_norm + 0.10·mood_bonus
```

Los pesos son hipótesis iniciales; se recalibrarán con regresión lineal tras 30–60 días de datos.

---

## 🛠️ Tecnologías

| Área | Stack |
|------|-------|
| **Backend** | FastAPI, Python 3.11+, SQLModel, SQLite |
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS |
| **UI Components** | Radix UI, shadcn/ui, Lucide Icons |
| **RAG** | LangChain, ChromaDB, Sentence Transformers, OpenAI (GPT-4o mini), Tavily |
| **Bio** | SQLModel, NumPy, Pandas, SciPy |
| **Documentos** | PyPDF, tiktoken, PyYAML |
| **Caché** | Redis |
| **Visualización** | Recharts, ReactFlow, Plotly |
| **Markdown** | react-markdown, KaTeX (LaTeX) |

---

## 🗺️ Roadmap

### ✅ Completado

- [x] Módulo 1 — Data pipeline (PDFs, chunking, vectorización, ChromaDB)
- [x] Módulo 2 — Core RAG (LLM, retrieval, perfil, modo socrático, router web)
- [x] Módulos 3.1–3.5 — Modelado, ingesta Suunto, métricas, ICD, motor de decisión
- [x] Dashboard Next.js — Interfaz completa con todas las funcionalidades
- [x] API REST FastAPI — Backend completo con streaming
- [x] Sistema de caché — Redis para RAG y sesiones
- [x] Mapa mental — Generación de grafos de conceptos
- [x] Plan de estudio — Rutas progresivas estructuradas

### 🚧 En desarrollo

- [ ] Módulo 3.6 — Registro post-sesión (formulario `StudySession`)
- [ ] Módulo 3.7 — Correlación semanal (HRV vs. rendimiento, confounders)
- [ ] Optimizaciones de rendimiento — Caché más agresivo, lazy loading

### 📋 Planificado

- [ ] Módulo 4 — Análisis avanzado: correlaciones, predicciones
- [ ] Módulo 5 — DevOps: CI/CD, Docker, despliegue
- [ ] Exportación de datos — CSV, JSON para análisis externo
- [ ] Integración con más wearables — Garmin, Apple Watch

Detalle por tareas y dificultad: [docs/TAREAS.md](docs/TAREAS.md).

---

## 🧪 Tests

```bash
# Motor de decisión (25 tests)
pytest src/bio/test_decision.py -v

# Métricas derivadas
python src/bio/test_metrics.py

# Tests del sistema RAG
pytest tests/ -v
```

---

## 📚 Documentación

- [Guía de Embeddings](docs/EMBEDDINGS_GUIDE.md) — Vectorización y ChromaDB
- [Tareas del proyecto](docs/TAREAS.md) — Roadmap por módulos
- [Resumen Bio-Adaptabilidad](docs/RESUMEN_TAREAS_3_3.4.md) — Tareas 3.3 y 3.4
- [SQL y ChromaDB](scripts/db/README.md) — Consultas y análisis
- [API Documentation](apps/dashboard/api/README.md) — Documentación de endpoints

---

## 🔧 Troubleshooting

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError: sentence_transformers` | `pip install sentence-transformers torch` |
| ChromaDB: *collection already exists with different embedding dimension* | `db.reset_collection()` y re-vectorizar |
| PDFs no se procesan | Sin contraseña; escaneados requieren OCR (no incluido). Revisar `logs/pdf_extraction.log` |
| Error de conexión a Redis | Verificar que Redis esté corriendo: `redis-cli ping` |
| Frontend no conecta con API | Verificar que FastAPI esté en `http://localhost:8000` y CORS configurado |
| Error de memoria al procesar PDFs grandes | Reducir `chunk_size` en `pdf_reader.py` o procesar PDFs en lotes |

---

## 👤 Autor y licencia

**David Arroyo** — Proyecto de sistema RAG adaptativo para aprendizaje en Data Science (contexto universitario).

Código abierto para fines educativos. Última actualización: febrero 2026.

---

## 📝 Notas adicionales

- El sistema está diseñado para funcionar principalmente en local, con mínima dependencia de servicios externos
- Los datos biométricos se almacenan localmente en SQLite para privacidad
- El modelo de embeddings se descarga automáticamente en la primera ejecución (~500 MB)
- Se recomienda tener al menos 8 GB de RAM para un rendimiento óptimo

---

**¿Preguntas o sugerencias?** Abre un issue o contacta al autor.
