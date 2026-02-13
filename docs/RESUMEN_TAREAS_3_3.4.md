# Resumen de Implementación: Tareas 3.1 - 3.4

## Módulo 3: Bio-Adaptabilidad (The Planner)

Este documento resume todo lo implementado en las tareas 3.1 hasta 3.4 del proyecto Dialektos, relacionado con el sistema de adaptación basado en Índice Cognitivo Diario (ICD).

---

## 📊 Tarea 3.1: Modelado de Datos (Esquema Completo)

### Estado: ✅ Completado

Se implementó un esquema de base de datos tipo **Star Schema** con tres tablas principales usando SQLModel:

### 3.1.1 Tabla `DailyBiometrics` (Tabla de Hechos)

**Ubicación:** `src/bio/models.py`

**Estructura:**
- **PK:** `date` (DATE) - Una fila por día
- **Datos Objetivos (Suunto):**
  - `hrv_rmssd` (FLOAT): HRV nocturna RMSSD en ms
  - `resting_hr` (INT): Frecuencia cardíaca en reposo
  - `avg_hr_sleep` (FLOAT): FC promedio durante el sueño
  - `sleep_total_min` (INT): Tiempo total de sueño
  - `deep_sleep_min`, `rem_sleep_min`, `light_sleep_min`, `awake_min` (INT)
  - `sleep_start_time` (VARCHAR): Hora de inicio del sueño (HH:MM)
  - `sleep_quality` (INT, 0-100): Score de calidad de sueño Suunto
  - `body_resources` (INT, 0-100): **Feature clave** - Índice integrado de recuperación Suunto
  - `training_load` (FLOAT): Carga de entrenamiento acumulada

- **Datos Subjetivos (Usuario):**
  - `energy_level` (INT, 1-10): Sensación de energía física
  - `mental_clarity` (INT, 1-10): Claridad mental (ortogonal a energy)
  - `mood` (VARCHAR, Enum): `focused` / `anxious` / `tired` / `neutral`
  - `motivation` (INT, 1-10): Ganas de estudiar
  - `muscle_soreness` (INT, 1-10): Fatiga física

- **Métricas Derivadas (calculadas automáticamente):**
  - `ln_rmssd` (FLOAT): Logaritmo natural de HRV (normalización)
  - `hrv_baseline_7d` (FLOAT): EMA 7 días de ln_rmssd (baseline personal)
  - `sleep_consistency` (FLOAT): Std dev de hora de dormir (7 días)
  - `icd_score` (FLOAT, 0-100): Índice Cognitivo Diario

**Validaciones:**
- Validadores Pydantic para rangos (energy_level 1-10, sleep_quality 0-100, etc.)
- Validación de enum para `mood`

### 3.1.2 Tabla `StudySession` (Eventos de Estudio)

**Ubicación:** `src/bio/models.py`

**Estructura:**
- **PK:** `session_id` (INT, autoincrement)
- **FK:** `date` → `DailyBiometrics.date`
- **Campos:**
  - `start_time`, `end_time` (DATETIME)
  - `duration_min` (INT): Tiempo real enfocado
  - `task_type` (VARCHAR, Enum): `theory_new` / `review` / `creative` / `coding` / `math`
  - `difficulty_attempted` (VARCHAR, Enum): `EASY` / `MEDIUM` / `HARD` / `EPIC`
  - `focus_score` (INT, 1-10): Dificultad para concentrarse (post-sesión)
  - `comprehension_rate` (INT, 0-100%): Auto-evaluación de comprensión
  - `retention_24h` (INT, 0-100%): Evaluación al día siguiente (opcional)
  - `flow_state` (BOOL): ¿Entraste en flow?
  - `interruptions` (INT): Número de interrupciones
  - `icd_at_start` (FLOAT): Snapshot del ICD al inicio (para correlación)

**Validaciones:**
- Validadores Pydantic para `task_type` y `difficulty_attempted` (enums)

### 3.1.3 Tabla `DailyConfounders` (Variables de Confusión)

**Ubicación:** `src/bio/models.py`

**Estructura:**
- **PK:** `date` (DATE, FK → `DailyBiometrics.date`, relación 1:1)
- **Campos:**
  - `caffeine_mg` (INT): Estimación de cafeína consumida
  - `screen_time_pre_sleep` (INT, min): Minutos de pantalla antes de dormir
  - `meals_quality` (INT, 1-5): Calidad percibida de alimentación
  - `social_stress` (INT, 1-10): Estrés social/emocional
  - `exercise_type` (VARCHAR, Enum): `none` / `light` / `moderate` / `intense`
  - `exercise_min` (INT): Minutos de ejercicio
  - `notes` (TEXT): Texto libre para contexto cualitativo

**Validaciones:**
- Validador Pydantic para `exercise_type` (enum)

### Configuración de Base de Datos

**Ubicación:** `src/bio/db.py`

- Función `get_engine()`: Crea motor SQLAlchemy para SQLite
- Función `create_tables()`: Crea todas las tablas del esquema
- Función `init_metrics_db()`: Inicializa la base de datos
- **Ruta por defecto:** `data/metrics.db`

---

## 📥 Tarea 3.2: Ingesta de Datos Suunto

### Estado: ✅ Completado

**Ubicación:** `src/bio/suunto_parser.py` (asumido, no revisado en detalle)

**Funcionalidad:**
- Parser de exportación Suunto (JSON/FIT)
- Extrae campos del esquema `DailyBiometrics` (objetivo)
- Estrategia: Ingesta manual primero, automatización con API después

---

## 🔧 Tarea 3.3: Feature Engineering (Normalización y Baseline)

### Estado: ✅ Completado

**Ubicación:** `src/bio/metrics.py`

### 3.3.1 Métricas Derivadas Implementadas

#### 1. `ln_rmssd` (Logaritmo Natural de HRV)

**Función:** `compute_ln_rmssd(hrv_rmssd: Optional[float]) -> Optional[float]`

**Lógica:**
- Calcula `ln(hrv_rmssd)` si el valor es válido (> 0)
- Normaliza la distribución log-normal de HRV a una distribución más gaussiana
- Estándar en la literatura de HRV

#### 2. `hrv_baseline_7d` (Baseline Personal de HRV)

**Función:** `compute_hrv_baseline_7d(session, date, ln_rmssd) -> Optional[float]`

**Lógica:**
- Consulta los últimos 7 días de registros
- Calcula **Media Móvil Exponencial (EMA)** con `span=7` usando pandas
- Se adapta gradualmente a cambios en el fitness del usuario
- Requiere al menos 2 valores válidos para calcular

**Implementación:**
```python
series = pd.Series(ln_values, index=dates)
ema = series.ewm(span=7, adjust=False).mean()
return float(ema.iloc[-1])
```

#### 3. `sleep_consistency` (Consistencia Circadiana)

**Función:** `compute_sleep_consistency(session, date, sleep_start_time) -> Optional[float]`

**Lógica:**
- Convierte `sleep_start_time` (formato "HH:MM") a minutos desde medianoche
- Consulta los últimos 7 días de registros
- Calcula **desviación estándar** de las horas de dormir
- Valores bajos = horarios consistentes, valores altos = irregularidad
- Requiere al menos 2 valores válidos

**Función auxiliar:** `_time_to_minutes(time_str)` convierte "HH:MM" a minutos

#### 4. Estadísticas de Baseline para Z-Scores

**Función:** `compute_sleep_quality_baseline(session, date, sleep_quality) -> Tuple[float, float]`

**Lógica:**
- Consulta los últimos 14 días de registros
- Calcula media y desviación estándar de `sleep_quality`
- Se usa para calcular Z-scores en el algoritmo ICD
- Requiere al menos 2 valores válidos

**Función auxiliar:** `compute_z_score(value, mean, std_dev) -> float`
- Calcula Z-score: `(valor - media) / desviación_estándar`
- Maneja casos edge (None, std_dev = 0)

### Función Principal: `compute_derived_metrics()`

**Función:** `compute_derived_metrics(session, record) -> DailyBiometrics`

**Lógica:**
1. Calcula `ln_rmssd` desde `hrv_rmssd`
2. Calcula `hrv_baseline_7d` (requiere consultar BD)
3. Calcula `sleep_consistency` (requiere consultar BD)
4. Calcula `icd_score` (requiere todas las métricas anteriores)

**Debe llamarse antes de insertar/actualizar** un registro para garantizar que las métricas derivadas estén calculadas.

---

## 🧮 Tarea 3.4: Algoritmo ICD (Índice Cognitivo Diario)

### Estado: ✅ Completado

**Ubicación:** `src/bio/metrics.py`

### 3.4.1 Función `calculate_icd()`

**Función:** `calculate_icd(session, record, weights=None) -> Optional[float]`

**Fórmula Implementada:**
```
ICD_raw = w1·Z(ln_rmssd) + w2·Z(sleep_quality) + w3·body_resources_norm
        + w4·energy_norm + w5·mental_clarity_norm + w6·mood_bonus

ICD = clip(50 + (ICD_raw * 16.67), 0, 100)
```

**Pesos por Defecto (Hipótesis Inicial):**
- `ln_rmssd`: 0.25 (métrica biológica clave)
- `sleep_quality`: 0.20 (calidad de sueño)
- `body_resources`: 0.20 (recursos corporales Suunto)
- `energy`: 0.15 (energía física percibida)
- `mental_clarity`: 0.10 (claridad mental)
- `mood`: 0.10 (estado de ánimo)

**Lógica de Cálculo:**

1. **Z-Scores para Métricas Biológicas:**
   - `Z(ln_rmssd)`: Usa `hrv_baseline_7d` como media y calcula std_dev de últimos 14 días
   - `Z(sleep_quality)`: Usa `compute_sleep_quality_baseline()` para media y std_dev

2. **Normalización Min-Max para Métricas Subjetivas (0-1):**
   - `body_resources_norm`: `body_resources / 100.0` (ya está en 0-100)
   - `energy_norm`: `(energy_level - 1) / 9.0` (de 1-10 a 0-1)
   - `mental_clarity_norm`: `(mental_clarity - 1) / 9.0` (de 1-10 a 0-1)

3. **Mood Bonus:**
   - `focused`: +1.0
   - `neutral`: +0.0
   - `anxious`: -0.3
   - `tired`: -0.5

4. **Combinación y Escalado:**
   - Multiplica cada componente por su peso
   - Suma todos los componentes → `ICD_raw`
   - Escala a rango 0-100: `50 + (ICD_raw * 16.67)`
   - Aplica clipping: `max(0.0, min(100.0, icd_score))`

**Validaciones:**
- Valida que los pesos sumen 1.0 (tolerancia 0.01)
- Maneja valores None retornando None si no hay suficientes datos
- Maneja casos edge (std_dev = 0, valores None)

**Nota:** Los pesos son **hipótesis iniciales**. Tras 30-60 días de datos, se recalibrarán con regresión lineal donde `Y = focus_score` (Tarea 3.7).

---

## 📁 Estructura de Archivos Implementados

```
src/bio/
├── models.py          # Modelos SQLModel (DailyBiometrics, StudySession, DailyConfounders)
├── db.py              # Configuración de base de datos (get_engine, create_tables)
├── metrics.py         # Cálculo de métricas derivadas y algoritmo ICD
└── suunto_parser.py   # Parser de datos Suunto (asumido)

data/
└── metrics.db         # Base de datos SQLite (se crea automáticamente)

scripts/
└── explore_data.sql   # Script SQL para explorar los datos
```

---

## 🔍 Cómo Usar el Script SQL

Para explorar todos los datos almacenados:

```bash
# Desde terminal
sqlite3 data/metrics.db < scripts/explore_data.sql

# O desde Python
import sqlite3
conn = sqlite3.connect('data/metrics.db')
with open('scripts/explore_data.sql', 'r') as f:
    conn.executescript(f.read())
```

El script incluye:
1. Estructura de tablas
2. Resumen de datos (conteos)
3. Datos completos de DailyBiometrics
4. Métricas derivadas calculadas
5. Análisis del ICD (estadísticas, distribución por rangos)
6. Sesiones de estudio
7. Variables de confusión
8. Vista integrada (JOIN de todas las tablas)
9. Análisis exploratorio de correlaciones
10. Validación de datos (detección de problemas)
11. Resumen final

---

## 📊 Rangos del ICD (Para Tarea 3.5)

Los rangos del ICD están definidos en `docs/TAREAS.md` § 3.5.1:

- **ICD > 80 (Peak):** "Deep Work" - Temas nuevos, Matemáticas complejas
- **ICD 50-80 (Normal):** "Flow" - Práctica de programación, ejercicios estándar
- **ICD 30-50 (Fatigue):** "Review" - Repaso espaciado, lectura de documentación
- **ICD < 30 (Burnout):** "Survival" - Solo vídeos o audios, nada de input activo

---

## ✅ Checklist de Implementación

- [x] **3.1.1** Tabla `DailyBiometrics` con todos los campos (objetivo + subjetivo + derivados)
- [x] **3.1.2** Tabla `StudySession` con FK a DailyBiometrics
- [x] **3.1.3** Tabla `DailyConfounders` con FK a DailyBiometrics (1:1)
- [x] **3.2.1** Parser de datos Suunto (asumido implementado)
- [x] **3.3.1** Cálculo de `ln_rmssd`
- [x] **3.3.1** Cálculo de `hrv_baseline_7d` (EMA 7 días)
- [x] **3.3.1** Cálculo de `sleep_consistency` (std dev hora dormir)
- [x] **3.4.1** Implementación completa de `calculate_icd()` con:
  - Z-scores para métricas biológicas
  - Normalización min-max para métricas subjetivas
  - Mood bonus
  - Combinación con pesos
  - Escalado a rango 0-100
- [x] Función `compute_derived_metrics()` que calcula todas las métricas automáticamente
- [x] Validadores Pydantic para todos los enums y rangos
- [x] Script SQL para explorar los datos

---

## 🚀 Próximos Pasos (Tareas Pendientes)

- [ ] **3.5.1** Mapeo ICD → Estrategia Pedagógica (thresholding)
- [ ] **3.6.1** Sistema de Registro Post-Sesión (formulario Streamlit)
- [ ] **3.7.1** Script de Análisis Semanal (correlaciones, validación de pesos)

---

**Última actualización:** 2026-02-13  
**Autor:** David Arroyo  
**Proyecto:** Dialektos
