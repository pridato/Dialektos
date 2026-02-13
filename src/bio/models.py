"""
Modelos SQLModel - Módulo Bio-Adaptabilidad

Esquema de base de datos para métricas biométricas diarias.
Separación clara entre señal biológica (Suunto), percepción subjetiva (usuario)
y métricas derivadas (calculadas al insertar).

Referencia: docs/TAREAS.md § 3.1.1

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

import math
from datetime import date as date_type, datetime
from enum import Enum
from typing import Optional

from pydantic import field_validator
from sqlmodel import Field, SQLModel


class MoodEnum(str, Enum):
    """
    Estados de ánimo para autoevaluación subjetiva.

    Ortogonal a energy_level y mental_clarity:
    puedes tener alta energía pero ánimo ansioso, o baja energía con focus.
    """
    FOCUSED = "focused"
    ANXIOUS = "anxious"
    TIRED = "tired"
    NEUTRAL = "neutral"


class TaskTypeEnum(str, Enum):
    """
    Tipos de tareas de estudio.

    Permite análisis granular: ¿en qué tipo de tarea rindes más
    cuando el ICD es bajo?
    """
    THEORY_NEW = "theory_new"
    REVIEW = "review"
    CREATIVE = "creative"
    CODING = "coding"
    MATH = "math"


class DifficultyEnum(str, Enum):
    """
    Niveles de dificultad intentados durante la sesión.

    Permite validar si la dificultad intentada vs. el ICD predice
    si entras en flow state.
    """
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    EPIC = "EPIC"


class ExerciseTypeEnum(str, Enum):
    """
    Tipos de ejercicio realizados durante el día.

    Permite controlar el efecto del ejercicio como variable de confusión
    en el análisis de correlación HRV-rendimiento.
    """
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    INTENSE = "intense"


class DailyBiometrics(SQLModel, table=True):
    """
    Tabla de hechos: una fila por día.

    Combina datos objetivos de Suunto (wearable) con autoevaluación subjetiva.
    Los campos derivados se calculan al insertar (ver tareas 3.3 y 3.4).

    PK: date — Garantiza unicidad por día.
    """

    __tablename__ = "daily_biometrics"

    # --- Primary Key ---
    date: date_type = Field(
        primary_key=True, description="Fecha del registro (una fila por día)")

    # --- Objetivo (Suunto / Wearable) ---
    hrv_rmssd: Optional[float] = Field(
        default=None, description="HRV nocturna RMSSD (ms) — actividad parasimpática")
    resting_hr: Optional[int] = Field(
        default=None, description="Frecuencia cardíaca en reposo (bpm)")
    avg_hr_sleep: Optional[float] = Field(
        default=None, description="FC promedio durante el sueño (bpm)")
    sleep_total_min: Optional[int] = Field(
        default=None, description="Tiempo total de sueño (min)")
    deep_sleep_min: Optional[int] = Field(
        default=None, description="Minutos de sueño profundo")
    rem_sleep_min: Optional[int] = Field(
        default=None, description="Minutos de sueño REM")
    light_sleep_min: Optional[int] = Field(
        default=None, description="Minutos de sueño ligero")
    awake_min: Optional[int] = Field(
        default=None, description="Minutos despierto durante la noche")
    sleep_start_time: Optional[str] = Field(
        default=None, description="Hora de inicio del sueño (formato HH:MM)")
    sleep_quality: Optional[int] = Field(
        default=None, ge=0, le=100, description="Score calidad sueño Suunto (0-100)")
    body_resources: Optional[int] = Field(
        default=None, ge=0, le=100, description="Recursos corporales Suunto 0-100 — feature clave")
    training_load: Optional[float] = Field(
        default=None, description="Carga de entrenamiento acumulada")

    # --- Subjetivo (Usuario) ---
    energy_level: Optional[int] = Field(
        default=None, ge=1, le=10, description="Sensación de energía física (1-10)")
    mental_clarity: Optional[int] = Field(
        default=None, ge=1, le=10, description="Claridad mental — niebla vs agudeza (1-10)")
    mood: Optional[str] = Field(
        default=None, description="focused / anxious / tired / neutral")
    motivation: Optional[int] = Field(
        default=None, ge=1, le=10, description="Ganas de estudiar (1-10)")
    muscle_soreness: Optional[int] = Field(
        default=None, ge=1, le=10, description="Fatiga física / agujetas (1-10)")

    # --- Derivados (calculados al insertar — tareas 3.3, 3.4) ---
    ln_rmssd: Optional[float] = Field(
        default=None, description="ln(hrv_rmssd) — normaliza distribución HRV")
    hrv_baseline_7d: Optional[float] = Field(
        default=None, description="EMA 7 días de ln_rmssd — línea base personal")
    sleep_consistency: Optional[float] = Field(
        default=None, description="Std dev hora dormir (7 días) — salud circadiana")
    icd_score: Optional[float] = Field(
        default=None, ge=0, le=100, description="Índice Cognitivo Diario (0-100)")

    @field_validator("mood", mode="before")
    @classmethod
    def validate_mood(cls, v: Optional[str]) -> Optional[str]:
        """Valida que mood esté en el enum permitido."""
        if v is None or v == "":
            return None
        allowed = {m.value for m in MoodEnum}
        normalized = str(v).strip().lower()
        if normalized not in allowed:
            raise ValueError(f"mood debe ser uno de: {sorted(allowed)}")
        return normalized

    def compute_ln_rmssd(self) -> Optional[float]:
        """
        Calcula ln(hrv_rmssd) si hrv_rmssd es válido.

        La HRV sigue distribución log-normal; ln() la normaliza para análisis.
        """
        if self.hrv_rmssd is not None and self.hrv_rmssd > 0:
            return math.log(self.hrv_rmssd)
        return None


class StudySession(SQLModel, table=True):
    """
    Tabla de eventos de estudio: múltiples sesiones por día.

    Es la variable objetivo (Y) que valida si el ICD funciona.
    Cada sesión se enlaza al DailyBiometrics del día mediante FK date.

    Referencia: docs/TAREAS.md § 3.1.2
    """

    __tablename__ = "study_sessions"

    # --- Primary Key ---
    session_id: Optional[int] = Field(
        default=None,
        primary_key=True,
        description="ID único de sesión (autoincrement)"
    )

    # --- Foreign Key ---
    date: date_type = Field(
        foreign_key="daily_biometrics.date",
        description="Fecha del día (FK → DailyBiometrics)"
    )

    # --- Tiempo ---
    start_time: datetime = Field(description="Hora de inicio de la sesión")
    end_time: Optional[datetime] = Field(
        default=None, description="Hora de fin de la sesión")
    duration_min: Optional[int] = Field(
        default=None, description="Tiempo real enfocado (minutos)")

    # --- Tipo y Dificultad ---
    task_type: Optional[str] = Field(
        default=None,
        description="Tipo de tarea: theory_new / review / creative / coding / math"
    )
    difficulty_attempted: Optional[str] = Field(
        default=None,
        description="Dificultad intentada: EASY / MEDIUM / HARD / EPIC"
    )

    # --- Métricas de Rendimiento ---
    focus_score: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="¿Cuánto te costó concentrarte? (1-10, post-sesión)"
    )
    comprehension_rate: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Auto-evaluación de comprensión al final (0-100%)"
    )
    retention_24h: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Evaluación de retención al día siguiente (0-100%, opcional para lag analysis)"
    )

    # --- Estado de Flow ---
    flow_state: Optional[bool] = Field(
        default=None,
        description="¿Entraste en estado de flow? Sí/No"
    )

    # --- Interrupciones ---
    interruptions: Optional[int] = Field(
        default=None,
        ge=0,
        description="Número de interrupciones durante la sesión"
    )

    # --- Snapshot del ICD ---
    icd_at_start: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Snapshot del ICD al momento de empezar (para correlación directa)"
    )

    @field_validator("task_type", mode="before")
    @classmethod
    def validate_task_type(cls, v: Optional[str]) -> Optional[str]:
        """Valida que task_type esté en el enum permitido."""
        if v is None or v == "":
            return None
        allowed = {t.value for t in TaskTypeEnum}
        normalized = str(v).strip().lower()
        if normalized not in allowed:
            raise ValueError(f"task_type debe ser uno de: {sorted(allowed)}")
        return normalized

    @field_validator("difficulty_attempted", mode="before")
    @classmethod
    def validate_difficulty(cls, v: Optional[str]) -> Optional[str]:
        """Valida que difficulty_attempted esté en el enum permitido."""
        if v is None or v == "":
            return None
        allowed = {d.value for d in DifficultyEnum}
        normalized = str(v).strip().upper()
        if normalized not in allowed:
            raise ValueError(
                f"difficulty_attempted debe ser uno de: {sorted(allowed)}")
        return normalized


class DailyConfounders(SQLModel, table=True):
    """
    Tabla de variables de confusión: una fila por día (1:1 con DailyBiometrics).

    Controla factores que pueden causar correlaciones espurias en el análisis
    HRV-rendimiento. Sin esto, solo mides asociación, no causalidad.

    Ejemplo: "HRV alta → buen focus" pero en realidad los días de HRV alta
    son los que no tomaste café tarde.

    Referencia: docs/TAREAS.md § 3.1.3
    """

    __tablename__ = "daily_confounders"

    # --- Primary Key y Foreign Key ---
    date: date_type = Field(
        primary_key=True,
        foreign_key="daily_biometrics.date",
        description="Fecha del registro (PK, FK → DailyBiometrics, 1:1)"
    )

    # --- Cafeína y Sustancias ---
    caffeine_mg: Optional[int] = Field(
        default=None,
        ge=0,
        description="Estimación de cafeína consumida (mg). Café ~95mg, té ~47mg"
    )

    # --- Hábitos de Sueño ---
    screen_time_pre_sleep: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minutos de pantalla antes de dormir"
    )

    # --- Alimentación y Estrés ---
    meals_quality: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Calidad percibida de alimentación (1-5)"
    )
    social_stress: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Estrés social/emocional no medido por Suunto (1-10)"
    )

    # --- Ejercicio ---
    exercise_type: Optional[str] = Field(
        default=None,
        description="Tipo de ejercicio: none / light / moderate / intense"
    )
    exercise_min: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minutos de ejercicio realizados"
    )

    # --- Notas Cualitativas ---
    notes: Optional[str] = Field(
        default=None,
        description="Texto libre para contexto cualitativo adicional"
    )

    @field_validator("exercise_type", mode="before")
    @classmethod
    def validate_exercise_type(cls, v: Optional[str]) -> Optional[str]:
        """Valida que exercise_type esté en el enum permitido."""
        if v is None or v == "":
            return None
        allowed = {e.value for e in ExerciseTypeEnum}
        normalized = str(v).strip().lower()
        if normalized not in allowed:
            raise ValueError(
                f"exercise_type debe ser uno de: {sorted(allowed)}")
        return normalized
