# Dialektos - Descripción para LinkedIn

## Versión Corta (para publicaciones)

🚀 **Dialektos** - Sistema RAG Adaptativo con Bio-Adaptabilidad

Desarrollé un asistente de aprendizaje inteligente que combina:
• **RAG (Retrieval-Augmented Generation)** sobre apuntes propios con búsqueda semántica vectorial
• **Índice Cognitivo Diario (ICD)** que adapta la dificultad del estudio según estado físico/mental
• **Motor pedagógico** que ajusta estrategias (Deep Work, Flow, Review, Survival) según biométricas
• **Modo socrático** para aprendizaje activo mediante cuestionamiento guiado

**Stack:** Python, Next.js, TypeScript, ChromaDB, SQLite, OpenAI GPT-4o, LangChain, Sentence Transformers

---

## Versión Media (para "Acerca de" o proyectos destacados)

### Dialektos: Sistema RAG Adaptativo con Bio-Adaptabilidad

**Proyecto personal** | Python + Next.js | Febrero 2026

Sistema de aprendizaje personalizado que integra tres pilares:

**1. RAG sobre Material Propio**
- Pipeline ETL para procesamiento de PDFs (extracción, chunking inteligente, limpieza)
- Búsqueda semántica vectorial multilingüe con ChromaDB (embeddings `paraphrase-multilingual-mpnet-base-v2`)
- Router inteligente: apuntes locales vs. búsqueda web (Tavily) según similitud semántica
- Integración GPT-4o para respuestas contextualizadas

**2. Bio-Adaptabilidad con Índice Cognitivo Diario (ICD)**
- Score 0-100 combinando biométricas objetivas (HRV/RMSSD, sueño, body resources Suunto), autoevaluación subjetiva (energía, claridad mental) y métricas derivadas (ln_rmssd, EMA 7 días)
- Clasificación en zonas cognitivas: Deep Work (>80), Flow (50-80), Review (30-50), Survival (<30)
- Estrategias pedagógicas adaptativas según estado del usuario

**3. Interfaz Moderna**
- Dashboard Next.js con glassmorphism y modo oscuro
- Visualizaciones interactivas (Recharts) de correlaciones biométricas
- Chat socrático con streaming en tiempo real
- Tracking de sesiones de estudio con métricas de rendimiento

**Stack:** Python 3.11+, LangChain, ChromaDB, SQLModel, SQLite, Next.js 16, TypeScript, React 19, Tailwind CSS, OpenAI GPT-4o, Sentence Transformers

**Logros:** Sistema funcional con persistencia local, motor de decisión con 25+ tests, pipeline automatizado de ingesta Suunto, dashboard responsive.

---

## Versión Extendida (para sección de proyectos detallada)

### Dialektos: Sistema RAG Adaptativo con Bio-Adaptabilidad

**Rol:** Desarrollador Full-Stack | **Stack:** Python, Next.js, TypeScript, ChromaDB, SQLite, OpenAI  
**Estado:** MVP funcional | **Fecha:** Febrero 2026

#### Descripción

Dialektos es un asistente de estudio que combina RAG (Retrieval-Augmented Generation) con análisis de biométricas para personalizar la experiencia de aprendizaje. El sistema adapta la dificultad y estrategia de estudio según el estado físico y mental del usuario, calculado mediante un Índice Cognitivo Diario (ICD).

#### Arquitectura

**1. Pipeline RAG (Backend Python)**

Pipeline ETL modular para procesamiento de PDFs: extracción con PyPDF, chunking inteligente (1000 tokens, overlap 200), limpieza de texto con RegEx, y extracción de metadatos estructurados (asignatura, tipo, idioma).

Vectorización con embeddings multilingües (`paraphrase-multilingual-mpnet-base-v2`) y persistencia en ChromaDB con batch processing optimizado (32 docs/batch). Búsqueda semántica con filtros por metadata y router inteligente: si similitud < 0.7 → búsqueda web automática (Tavily API).

Motor de razonamiento con GPT-4o mini, memoria conversacional multi-turno, modo socrático mediante prompts especializados, e inyección de perfil de usuario para personalización.

**2. Motor de Bio-Adaptabilidad**

Modelo de datos tipo Star Schema en SQLite: tabla de hechos `DailyBiometrics` (PK: date) con datos objetivos (Suunto) y subjetivos, dimensiones `StudySession` y `DailyConfounders`, ORM con SQLModel.

Cálculo del ICD mediante fórmula ponderada: 25% Z-score ln(RMSSD), 20% calidad de sueño, 20% body_resources, 15% energía, 10% claridad mental, 10% bonus ánimo. Feature engineering con EMA 7 días para baseline personal y consistencia circadiana.

Motor de decisión pedagógica clasifica en 4 zonas: **Deep Work** (ICD > 80): temas nuevos, socrático activo, ejercicios desafiantes; **Flow** (50-80): práctica guiada, ejercicios estándar; **Review** (30-50): repaso espaciado, contenido pasivo; **Survival** (< 30): solo lectura, evitar carga cognitiva alta.

**3. Dashboard Next.js**

Arquitectura: Next.js 16 con App Router, TypeScript end-to-end, Tailwind CSS con glassmorphism, componentes accesibles con Radix UI.

Vistas: Dashboard con ICD visual y métricas biométricas en tiempo real; Chat Socrático tipo ChatGPT con streaming y soporte LaTeX; Bio-Tracker para ingesta manual; Analíticas con visualizaciones de correlaciones; Sesión Focus con timer y tracking de distracciones.

Características UX: diseño responsive, visualizaciones interactivas (Recharts), auto-scroll en chat, precalentamiento del backend para latencia mínima.

#### Logros Técnicos

✅ Pipeline ETL robusto con manejo de errores y logging detallado  
✅ Búsqueda semántica optimizada con batch processing y router inteligente  
✅ Motor de decisión validado con 25+ tests unitarios  
✅ Arquitectura modular (ingest, brain, bio)  
✅ Persistencia local (ChromaDB y SQLite) sin dependencias externas excepto APIs de IA  
✅ UI/UX moderna con glassmorphism, modo oscuro, visualizaciones interactivas  

#### Stack Tecnológico

**Backend:** Python 3.11+, LangChain, ChromaDB, SQLModel, SQLite, NumPy, Pandas, Sentence Transformers, OpenAI API, Tavily API, PyPDF, tiktoken, PyYAML

**Frontend:** Next.js 16, React 19, TypeScript 5.7, Tailwind CSS, Radix UI, Recharts, React Markdown, KaTeX, Next Themes

**DevOps:** Git, Pytest, logging estructurado, documentación técnica completa

#### Impacto y Aprendizajes

Dominio de arquitecturas RAG, embeddings vectoriales y sistemas adaptativos. Experiencia en diseño de pipelines ETL, arquitectura modular y type safety. Feature engineering, normalización estadística y análisis de correlaciones. Diseño de interfaces modernas, optimización de rendimiento y accesibilidad.

#### Roadmap

- Análisis de correlación semanal (HRV vs. rendimiento)
- Sistema de recomendaciones basado en historial
- Exportación de métricas y visualizaciones avanzadas
- Optimización de prompts para modo socrático

---

## Hashtags Sugeridos

#DataScience #MachineLearning #RAG #LLM #OpenAI #NextJS #TypeScript #Python #FullStack #Biohacking #QuantifiedSelf #EdTech #PersonalizedLearning #ChromaDB #LangChain #React #TailwindCSS #AI #DeepLearning #NLP

---

## Notas para Head Hunters

**Puntos Fuertes:**
1. **Full-Stack:** Backend (Python) y frontend (Next.js/TypeScript)
2. **IA/ML:** RAG, embeddings, LLMs, sistemas adaptativos
3. **Arquitectura:** Sistemas complejos con múltiples componentes integrados
4. **Ciencia de Datos:** Feature engineering, análisis estadístico, modelado
5. **Producto:** Visión end-to-end desde concepto hasta implementación

**Roles Apropiados:**
- Full-Stack Developer con enfoque en IA
- ML Engineer / AI Engineer
- Data Scientist con habilidades de desarrollo
- Software Engineer en productos EdTech
- Research Engineer en sistemas adaptativos
