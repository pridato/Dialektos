"""
Módulo Bio-Adaptabilidad - Proyecto Dialektos

Sistema basado en Índice Cognitivo Diario (ICD) que adapta la dificultad
del estudio según el estado fisiológico del usuario.

Modelos:
    - DailyBiometrics: Foto diaria biométrica (Suunto + autoevaluación)
    - MoodEnum: Estados de ánimo para métricas subjetivas

Motor de Decisión:
    - CognitiveZone: Zonas cognitivas derivadas del ICD
    - PedagogicalStrategy: Estrategia pedagógica asociada a cada zona
    - get_strategy(): Mapeo ICD → estrategia pedagógica

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

from src.bio.decision import (
    AIInteractionMode,
    CognitiveZone,
    PedagogicalStrategy,
    ThresholdConfig,
    get_strategy,
)
from src.bio.models import DailyBiometrics, MoodEnum

__all__ = [
    "DailyBiometrics",
    "MoodEnum",
    "CognitiveZone",
    "AIInteractionMode",
    "PedagogicalStrategy",
    "ThresholdConfig",
    "get_strategy",
]
