"""
Módulo Bio-Adaptabilidad - Proyecto Dialektos

Sistema basado en Índice Cognitivo Diario (ICD) que adapta la dificultad
del estudio según el estado fisiológico del usuario.

Modelos:
    - DailyBiometrics: Foto diaria biométrica (Suunto + autoevaluación)
    - MoodEnum: Estados de ánimo para métricas subjetivas

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

from src.bio.models import DailyBiometrics, MoodEnum

__all__ = ["DailyBiometrics", "MoodEnum"]
