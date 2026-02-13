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
from datetime import date as date_type
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


class DailyBiometrics(SQLModel, table=True):
    """
    Tabla de hechos: una fila por día.

    Combina datos objetivos de Suunto (wearable) con autoevaluación subjetiva.
    Los campos derivados se calculan al insertar (ver tareas 3.3 y 3.4).

    PK: date — Garantiza unicidad por día.
    """

    __tablename__ = "daily_biometrics"

    # --- Primary Key ---
    date: date_type = Field(primary_key=True, description="Fecha del registro (una fila por día)")

    # --- Objetivo (Suunto / Wearable) ---
    hrv_rmssd: Optional[float] = Field(default=None, description="HRV nocturna RMSSD (ms) — actividad parasimpática")
    hrv_sdnn: Optional[float] = Field(default=None, description="HRV SDNN (ms) — variabilidad total del intervalo RR")
    resting_hr: Optional[int] = Field(default=None, description="Frecuencia cardíaca en reposo (bpm)")
    avg_hr_sleep: Optional[float] = Field(default=None, description="FC promedio durante el sueño (bpm)")
    sleep_total_min: Optional[int] = Field(default=None, description="Tiempo total de sueño (min)")
    deep_sleep_min: Optional[int] = Field(default=None, description="Minutos de sueño profundo")
    rem_sleep_min: Optional[int] = Field(default=None, description="Minutos de sueño REM")
    light_sleep_min: Optional[int] = Field(default=None, description="Minutos de sueño ligero")
    awake_min: Optional[int] = Field(default=None, description="Minutos despierto durante la noche")
    sleep_quality: Optional[int] = Field(default=None, ge=0, le=100, description="Score calidad sueño Suunto (0-100)")
    body_resources: Optional[int] = Field(default=None, ge=0, le=100, description="Recursos corporales Suunto 0-100 — feature clave")
    stress_avg: Optional[float] = Field(default=None, description="Nivel medio estrés diurno")
    training_load: Optional[float] = Field(default=None, description="Carga de entrenamiento acumulada")

    # --- Subjetivo (Usuario) ---
    energy_level: Optional[int] = Field(default=None, ge=1, le=10, description="Sensación de energía física (1-10)")
    mental_clarity: Optional[int] = Field(default=None, ge=1, le=10, description="Claridad mental — niebla vs agudeza (1-10)")
    mood: Optional[str] = Field(default=None, description="focused / anxious / tired / neutral")
    motivation: Optional[int] = Field(default=None, ge=1, le=10, description="Ganas de estudiar (1-10)")
    muscle_soreness: Optional[int] = Field(default=None, ge=1, le=10, description="Fatiga física / agujetas (1-10)")

    # --- Derivados (calculados al insertar — tareas 3.3, 3.4) ---
    ln_rmssd: Optional[float] = Field(default=None, description="ln(hrv_rmssd) — normaliza distribución HRV")
    hrv_baseline_7d: Optional[float] = Field(default=None, description="EMA 7 días de ln_rmssd — línea base personal")
    sleep_consistency: Optional[float] = Field(default=None, description="Std dev hora dormir (7 días) — salud circadiana")
    icd_score: Optional[float] = Field(default=None, ge=0, le=100, description="Índice Cognitivo Diario (0-100)")

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
