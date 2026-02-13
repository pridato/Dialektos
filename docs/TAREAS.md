# Tareas - Proyecto Dialektos

## Leyenda de Dificultad

- **EASY:** Configuración, sintaxis básica, UI simple. (Ideal para días de cansancio).
- **MEDIUM:** Lógica de programación, manipulación de datos, APIs. (Requiere foco).
- **HARD:** Arquitectura compleja, recursividad, matemáticas, optimización. (Solo en *Flow State*).
- **EPIC:** Tareas grandes que requieren investigación previa.

---

## Módulo 1: Data Pipeline & Ingesta (RAG Backend)

*El cimiento. Sin esto, la IA no sabe nada de tus asignaturas.*

- [X] **Configuración del Entorno Virtual y Repositorio**
  - **Dificultad:** EASY
  - *Detalle:* `git init`, `venv`, `requirements.txt` (langchain, chromadb, pypdf, openai).

- [X] **Script ETL: Extracción de Texto (PDFs)**
  - **Dificultad:** MEDIUM
  - *Detalle:* Crear script que recorra una carpeta, lea PDFs y limpie caracteres extraños (saltos de línea, cabeceras repetitivas).

- [X] **Implementación de Chunking Inteligente**
  - **Dificultad:** MEDIUM
  - *Detalle:* Configurar `RecursiveCharacterTextSplitter`. No cortar frases a la mitad. Experimentar con chunk_size (ej. 1000 tokens).

- [X] **Vectorización (Embeddings)**
  - **Dificultad:** MEDIUM
  - *Detalle:* Convertir texto a vectores y guardarlos en `ChromaDB` (local). Persistencia de datos en disco.
  - *Completado:* 2026-02-12. Implementado con Sentence Transformers (paraphrase-multilingual-mpnet-base-v2). Ver `docs/EMBEDDINGS_GUIDE.md`

- [X] **Metadatos Estructurados**
  - **Dificultad:** HARD
  - *Detalle:* No guardar solo texto. Extraer y guardar metadata: `{asignatura: "Cálculo", tipo: "Teoría", fecha: "2024"}` para filtrado posterior.

---

## Módulo 2: Core Logic & Razonamiento (The Brain)

*Donde ocurre la magia. Aquí definimos cómo "piensa" la IA.*

- [X] **Conexión Básica LLM (Chat)**
  - **Dificultad:** EASY
  - *Detalle:* Función simple `query_llm(pregunta)` que retorna respuesta de GPT-4o.

- [X] **Retrieval System (Búsqueda)**
  - **Dificultad:** MEDIUM
  - *Detalle:* Lógica que busca los 3 chunks más relevantes en ChromaDB antes de enviarlos al LLM.

- [X] **Inyección de Perfil de Usuario (JSON)**
  - **Dificultad:** EASY
  - *Detalle:* Cargar `user_profile.json` (Goals: Data Scientist) e inyectarlo en el System Prompt dinámicamente.

- [X] **Prompt Engineering: "El Adversario"**
  - **Dificultad:** HARD
  - *Detalle:* Diseñar el prompt para que *cuestione* y *pida justificaciones*. Iterar hasta que deje de dar respuestas directas.

- [X] **Router de Búsqueda (Agente)**
  - **Dificultad:** HARD
  - *Detalle:* Lógica condicional: Si la similitud en la DB vectorial es baja (<0.7), activar búsqueda web (Tavily API), si es alta, usar apuntes.
  - *Completado:* 2026-02-12. Ver `src/brain/web_search.py` y lógica en `retriever.py`

---

## Módulo 3: Bio-Adaptabilidad (The Planner)

*Sistema basado en Índice Cognitivo Diario (ICD) que adapta la dificultad según tu estado fisiológico y valida correlaciones HRV-Rendimiento mediante normalización estadística avanzada. Modelo de datos tipo Star Schema: una tabla de hechos temporal (DailyBiometrics) con dimensiones para sesiones (StudySession) y confounders (DailyConfounders).*

### 3.1 Modelado de Datos: Esquema Completo (SQLModel)

*Crear la estructura de base de datos (`metrics.db`) usando SQLModel. Tres tablas interrelacionadas que separan señal biológica, percepción psicológica y variables de confusión.*

- [ ] **3.1.1 Tabla `DailyBiometrics` — La foto diaria (PK: `date`)**
  - **Dificultad:** EASY
  - *Detalle:* Una fila por día. Combina datos objetivos de Suunto con autoevaluación subjetiva.
  - *Esquema — Objetivo (Suunto):*
    - `hrv_rmssd` (FLOAT, ms): HRV nocturna, actividad parasimpática (recuperación).
    - `hrv_sdnn` (FLOAT, ms): Variabilidad total del intervalo RR (adaptabilidad general).
    - `resting_hr` (INT, bpm): Frecuencia cardíaca en reposo.
    - `avg_hr_sleep` (FLOAT, bpm): FC promedio durante el sueño.
    - `sleep_total_min` (INT): Tiempo total de sueño.
    - `deep_sleep_min` (INT): Minutos de sueño profundo.
    - `rem_sleep_min` (INT): Minutos de sueño REM.
    - `light_sleep_min` (INT): Minutos de sueño ligero.
    - `awake_min` (INT): Minutos despierto durante la noche.
    - `sleep_quality` (INT, 0-100): Score de calidad de sueño de Suunto.
    - `body_resources` (INT, 0-100): Métrica propietaria de Suunto — índice integrado de recuperación (combina HRV + sueño + estrés). **Feature clave.**
    - `stress_avg` (FLOAT): Nivel medio de estrés diurno (activación simpática sostenida).
    - `training_load` (FLOAT): Carga de entrenamiento acumulada.
  - *Esquema — Subjetivo (User):*
    - `energy_level` (INT, 1-10): Sensación de "pilas" (energía física).
    - `mental_clarity` (INT, 1-10): Claridad mental (niebla vs. agudeza). **Separado de energy — son ortogonales.**
    - `mood` (VARCHAR, Enum): `focused` / `anxious` / `tired` / `neutral`.
    - `motivation` (INT, 1-10): Ganas de estudiar (disposición volitiva).
    - `muscle_soreness` (INT, 1-10): Fatiga física / agujetas.
  - *Esquema — Derivados (calculados al insertar):*
    - `ln_rmssd` (FLOAT): `ln(hrv_rmssd)` — normaliza la distribución asimétrica de la HRV.
    - `hrv_baseline_7d` (FLOAT): EMA 7 días de `ln_rmssd` — tu línea base personal.
    - `sleep_consistency` (FLOAT): Std dev de la hora de dormir (últimos 7 días) — salud circadiana.
    - `icd_score` (FLOAT, 0-100): Índice Cognitivo Diario calculado (ver 3.3).
  - *Por qué:* Separar señal biológica de percepción psicológica. A veces divergen (buena HRV pero niebla mental, o baja HRV pero alta motivación), y esa divergencia es un insight valioso.

- [ ] **3.1.2 Tabla `StudySession` — Eventos de estudio (FK: `date`)**
  - **Dificultad:** EASY
  - *Detalle:* Múltiples sesiones por día. Es la **variable objetivo (Y)** que valida si el ICD funciona.
  - *Esquema:*
    - `session_id` (INT, PK, autoincrement).
    - `date` (DATE, FK → DailyBiometrics): Enlace al estado biométrico del día.
    - `start_time` (DATETIME): Hora de inicio.
    - `end_time` (DATETIME): Hora de fin.
    - `duration_min` (INT): Tiempo real enfocado.
    - `task_type` (VARCHAR, Enum): `theory_new` / `review` / `creative` / `coding` / `math`.
    - `difficulty_attempted` (VARCHAR, Enum): `EASY` / `MEDIUM` / `HARD` / `EPIC`.
    - `focus_score` (INT, 1-10): ¿Cuánto te costó concentrarte? (post-sesión).
    - `comprehension_rate` (INT, 0-100%): Auto-evaluación al final.
    - `retention_24h` (INT, 0-100%): Evaluación al día siguiente (opcional, para lag analysis).
    - `flow_state` (BOOL): ¿Entraste en estado de flow? Sí/No.
    - `interruptions` (INT): Número de interrupciones durante la sesión.
    - `icd_at_start` (FLOAT): Snapshot del ICD al momento de empezar (para correlación directa).
  - *Por qué:* Con `task_type`, `difficulty_attempted` y `flow_state` puedes hacer análisis mucho más ricos: ¿en qué tipo de tarea rindes más cuando el ICD es bajo? ¿La dificultad intentada vs. el ICD predice si entras en flow?

- [ ] **3.1.3 Tabla `DailyConfounders` — Variables de confusión (PK: `date`, 1:1 con DailyBiometrics)**
  - **Dificultad:** EASY
  - *Detalle:* Sin esto, tu análisis de correlación puede ser **espurio**. Ejemplo: "HRV alta → buen focus" pero en realidad los días de HRV alta son los que no tomaste café tarde.
  - *Esquema:*
    - `date` (DATE, PK, FK → DailyBiometrics).
    - `caffeine_mg` (INT): Estimación de cafeína consumida (café ~95mg, té ~47mg).
    - `alcohol` (BOOL): Consumo de alcohol la noche anterior.
    - `screen_time_pre_sleep` (INT, min): Minutos de pantalla antes de dormir.
    - `meals_quality` (INT, 1-5): Calidad percibida de alimentación.
    - `social_stress` (INT, 1-10): Estrés social/emocional no medido por Suunto.
    - `exercise_type` (VARCHAR, Enum): `none` / `light` / `moderate` / `intense`.
    - `exercise_min` (INT): Minutos de ejercicio.
    - `notes` (TEXT): Texto libre para contexto cualitativo.
  - *Por qué:* Controlar confounders es **obligatorio** para que tu Tarea 3.6 (correlación) tenga rigor estadístico. Sin esto, solo mides asociación, no causalidad.

### 3.2 Ingesta de Datos Suunto

- [ ] **3.2.1 Parser de Exportación Suunto (JSON/FIT)**
  - **Dificultad:** MEDIUM
  - *Detalle:* Crear script `src/bio/suunto_parser.py` que lea los archivos JSON exportados desde la Suunto App y extraiga los campos del esquema `DailyBiometrics` (objetivo).
  - *Estrategia:* Empezar con ingesta manual (exportar JSON → parsear → insertar). Automatizar con Suunto API (OAuth2) cuando haya 30+ días de datos y se confirme qué campos son realmente útiles.
  - *Por qué:* No invertir tiempo en automatización de API hasta validar el modelo de datos con datos reales.

### 3.3 Feature Engineering: Normalización y Baseline

- [ ] **3.3.1 Cálculo de Métricas Derivadas**
  - **Dificultad:** MEDIUM
  - *Detalle:* No guardar solo el dato crudo. Calcular al insertar cada registro:
    - `ln_rmssd`: `ln(hrv_rmssd)` — transforma la distribución log-normal de la HRV en una distribución más gaussiana.
    - `hrv_baseline_7d`: Media Móvil Exponencial (EMA, span=7) de `ln_rmssd` — tu "normal" personal, se adapta a cambios graduales de fitness.
    - `sleep_consistency`: Desviación estándar de la hora de dormir (ventana 7 días) — mide regularidad circadiana.
  - *Por qué:* Los modelos de ML funcionan mal con datos en escalas muy diferentes (HRV en ms vs Energy en 1-10). Normalizar es obligatorio. El `ln_rmssd` es estándar en la literatura de HRV.

### 3.4 Algoritmo ICD (Índice Cognitivo Diario)

- [ ] **3.4.1 Implementación de `calculate_icd(metrics)`**
  - **Dificultad:** HARD
  - *Detalle:* Función que pondera métricas biológicas y subjetivas en un score único 0-100.
  - *Fórmula Propuesta (pesos iniciales — hipótesis a validar con datos):*
    ```
    ICD = 0.25·Z(ln_rmssd) + 0.20·Z(sleep_quality) + 0.20·body_resources_norm
        + 0.15·energy_norm + 0.10·mental_clarity_norm + 0.10·mood_bonus
    ```
  - *Lógica:*
    - **Z-Score** para métricas biológicas: ¿cuántas desviaciones estándar te alejas de tu baseline personal?
    - **Min-Max normalization** (0-1) para métricas subjetivas.
    - **`mood_bonus`**: +1.0 si `focused`, +0.0 si `neutral`, -0.3 si `anxious`, -0.5 si `tired`.
    - Escalar resultado final a rango 0-100 con clipping.
  - *Salida:* Un valor 0-100 que determina el "ancho de banda cognitivo" del día.
  - *Nota:* Los pesos son **hipótesis iniciales**. Tras 30-60 días de datos, se recalibran con regresión lineal donde `Y = focus_score` y los features son las métricas (ver 3.7).

### 3.5 Motor de Decisión (Thresholding)

- [ ] **3.5.1 Mapeo ICD → Estrategia Pedagógica**
  - **Dificultad:** MEDIUM
  - *Detalle:* Mapear el ICD a una estrategia pedagógica concreta.
  - *Umbrales:*
    - **ICD > 80 (Peak):** "Deep Work". Temas nuevos, Matemáticas complejas, Prompt Socrático (La IA te interroga).
    - **ICD 50-80 (Normal):** "Flow". Práctica de programación, ejercicios estándar.
    - **ICD 30-50 (Fatigue):** "Review". Repaso espaciado (Anki style), lectura de documentación.
    - **ICD < 30 (Burnout):** "Survival". Solo vídeos o audios. Nada de input activo.
  - *Por qué:* Automatiza la decisión de "qué estudiar hoy" basándose en datos, evitando la parálisis por análisis.

### 3.6 Tracking de la Variable Objetivo (Y)

- [ ] **3.6.1 Sistema de Registro Post-Sesión**
  - **Dificultad:** EASY
  - *Detalle:* Formulario que se llena al terminar cada sesión de estudio (conectado con el formulario Streamlit del Módulo 4). Cada `StudySession` se enlaza automáticamente al `DailyBiometrics` del día y captura el `icd_at_start` como snapshot.
  - *Conexión:* FK `date` → `DailyBiometrics`. Permite múltiples sesiones por día.

### 3.7 Análisis de Correlación (The Data Scientist Job)

- [ ] **3.7.1 Script de Análisis Semanal (`src/bio/analysis.py`)**
  - **Dificultad:** EPIC
  - *Detalle:* Script que corre semanalmente y genera un reporte de correlaciones.
  - *Análisis:*
    - **Matriz de Correlación:** ¿Qué influye más en `focus_score`? ¿Es `ln_rmssd`, `body_resources`, o `energy_level`? → Heatmap con `seaborn`.
    - **Detección de Lag:** `shift()` en Pandas para ver si el sueño de anteayer afecta al estudio de hoy (lag de 1-3 días).
    - **Correlación Parcial:** Controlar confounders (`caffeine_mg`, `exercise_min`) para aislar el efecto real de cada feature.
    - **Validación de Pesos ICD:** Regresión lineal `focus_score ~ features` para comparar pesos aprendidos vs. pesos manuales de la fórmula ICD.
    - **Divergencia Objetivo-Subjetivo:** Scatter plot de `body_resources` vs. `energy_level` para detectar días donde biología y percepción divergen.
  - *Salida:* Reporte Markdown auto-generado en `docs/reports/` con gráficos y coeficientes.
  - *Requisito mínimo:* Alerta si datos < 30 días o correlación < 0.3 (insuficiente para conclusiones).
  - *Por qué:* Esto valida tu tesis. Si `energy_level` tiene r=0.8 con rendimiento y `ln_rmssd` solo r=0.2, aprendes que tu percepción es más fiable que tu reloj. Si los confounders explican más varianza que las biométricas, cambias la estrategia.

---

## Módulo 4: Interfaz de Usuario (Frontend Streamlit)

*Interfaz completa para ingreso de datos fisiológicos, visualización del ICD, tracking de sesiones y análisis de correlaciones.*

- [ ] **Estructura Base Streamlit con Layout Multi-Página**
  - **Dificultad:** EASY
  - *Detalle:* Configurar Streamlit con `st.set_page_config(layout="wide")`. Crear navegación multi-página: "Chat", "ICD Dashboard", "Tracking Sesiones", "Análisis Correlaciones". Sidebar con navegación y estado actual del ICD.

- [ ] **Página: Ingreso de Datos Fisiológicos (Suunto)**
  - **Dificultad:** EASY
  - *Detalle:* Formulario en sidebar o página dedicada con inputs: HRV nocturna (RMSSD), % Sueño profundo, % REM, Recursos al despertar (0-100). Botón "Guardar datos del día". Validación de rangos. Mostrar baseline actual calculado.

- [ ] **Página: Visualización del ICD en Tiempo Real**
  - **Dificultad:** MEDIUM
  - *Detalle:* Dashboard principal con: Gauge/Progress bar del ICD (0-100), desglose de componentes (HRV 40%, Sueño 30%, Recursos 30%), plan sugerido según ICD (badge con color: verde/amarillo/naranja/rojo), gráfico de tendencia últimos 7 días.

- [ ] **Página: Chat Principal con Modo Adaptativo**
  - **Dificultad:** MEDIUM
  - *Detalle:* Input de chat con streaming de respuestas (efecto máquina de escribir). Badge visible mostrando modo actual (Socrático Hardcore/Explicativo Suave/Repaso/Recuperación) según ICD. Integración con selector de prompts dinámico del módulo 3.

- [ ] **Página: Tracking de Sesiones de Estudio**
  - **Dificultad:** MEDIUM
  - *Detalle:* Formulario al finalizar sesión: Duración (horas), Tipo de tarea (selectbox: teoría nueva/repaso/creativo), RPE cognitivo (slider 1-10), Retención 24h (opcional, para sesiones anteriores). Tabla histórica de sesiones. Tracking pasivo automático (tiempo de sesión activa).

- [ ] **Página: Dashboard de Correlación HRV-Rendimiento**
  - **Dificultad:** HARD
  - *Detalle:* Visualización con Plotly/Matplotlib: Scatter plot HRV vs Horas de estudio, HRV vs RPE cognitivo, HRV vs Retención. Mostrar coeficiente de correlación de Pearson, línea de regresión. Alerta si datos < 30 días o correlación < 0.3. Tabla de estadísticas descriptivas.

- [ ] **Componentes UI Reutilizables**
  - **Dificultad:** MEDIUM
  - *Detalle:* Crear funciones helper: `render_icd_gauge()`, `render_study_plan_badge()`, `render_correlation_chart()`. Usar `st.metric()` para KPIs. Colores consistentes según rangos de ICD.

## Módulo 5: DevOps & Calidad

*Hacer las cosas bien como ingeniero.*

- [ ] **Gestión de Secretos (.env)**
  - **Dificultad:** EASY
  - *Detalle:* Ocultar API Keys.

- [ ] **Refactorización Modular**
  - **Dificultad:** MEDIUM
  - *Detalle:* Separar código en `/src/ingest`, `/src/brain`, `/src/ui`. Nada de código espagueti.

- [ ] **Documentación (README)**
  - **Dificultad:** EASY
  - *Detalle:* Escribir cómo instalar y usar el proyecto (vital para el portafolio).
