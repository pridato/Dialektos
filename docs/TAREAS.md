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

- [ ] **Metadatos Estructurados**
  - **Dificultad:** HARD
  - *Detalle:* No guardar solo texto. Extraer y guardar metadata: `{asignatura: "Cálculo", tipo: "Teoría", fecha: "2024"}` para filtrado posterior.

---

## Módulo 2: Core Logic & Razonamiento (The Brain)

*Donde ocurre la magia. Aquí definimos cómo "piensa" la IA.*

- [ ] **Conexión Básica LLM (Chat)**
  - **Dificultad:** EASY
  - *Detalle:* Función simple `query_llm(pregunta)` que retorna respuesta de GPT-4o.

- [ ] **Retrieval System (Búsqueda)**
  - **Dificultad:** MEDIUM
  - *Detalle:* Lógica que busca los 3 chunks más relevantes en ChromaDB antes de enviarlos al LLM.

- [ ] **Inyección de Perfil de Usuario (JSON)**
  - **Dificultad:** EASY
  - *Detalle:* Cargar `user_profile.json` (Goals: Data Scientist) e inyectarlo en el System Prompt dinámicamente.

- [ ] **Prompt Engineering: "El Adversario"**
  - **Dificultad:** HARD
  - *Detalle:* Diseñar el prompt para que *cuestione* y *pida justificaciones*. Iterar hasta que deje de dar respuestas directas.

- [ ] **Router de Búsqueda (Agente)**
  - **Dificultad:** HARD
  - *Detalle:* Lógica condicional: Si la similitud en la DB vectorial es baja (<0.7), activar búsqueda web (Tavily API), si es alta, usar apuntes.

---

## Módulo 3: Bio-Adaptabilidad (The Planner)

*El sistema que decide la dificultad según tu estado físico.*

- [ ] **Modelado de Datos de Estado**
  - **Dificultad:** EASY
  - *Detalle:* Definir la clase/diccionario `UserState` con atributos: `sleep_hours`, `training_load`, `energy_level`.

- [ ] **Motor de Reglas (Decision Engine)**
  - **Dificultad:** MEDIUM
  - *Detalle:* Lógica `if/else` compleja. Ej: `if training == 'Legs' and sleep < 6: mode = 'PASSIVE'`.

- [ ] **Selector de Prompts Dinámico**
  - **Dificultad:** MEDIUM
  - *Detalle:* Tener 3 plantillas de prompt distintas (Modo Socrático Hardcore, Modo Explicativo Suave, Modo Repaso) y cargar una según el motor de reglas.

- [ ] **Recomendador de Temas**
  - **Dificultad:** EPIC
  - *Detalle:* Algoritmo que cruza tu estado con el temario. Si estás cansado -> Sugerir temas marcados como "fáciles" o "repaso".

---

## Módulo 4: Interfaz de Usuario (Frontend Streamlit)

*Lo que ves y tocas. Debe ser rápido y sin fricción.*

- [ ] **Estructura Base Streamlit**
  - **Dificultad:** EASY
  - *Detalle:* Título, layout wide, input de chat.

- [ ] **Sidebar "Bio-Check"**
  - **Dificultad:** EASY
  - *Detalle:* Sliders y Radio Buttons para configurar el estado diario sin escribir.

- [ ] **Visualización de Chat (Streaming)**
  - **Dificultad:** MEDIUM
  - *Detalle:* Que el texto aparezca escribiéndose poco a poco (efecto máquina de escribir) para mejor UX.

- [ ] **Dashboard de Métricas (Feedback)**
  - **Dificultad:** HARD
  - *Detalle:* Gráficos simples con `matplotlib` o nativos de Streamlit que muestren correlación (Ej: "Rindes más los días de descanso").

---

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
