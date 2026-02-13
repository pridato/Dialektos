"""
Tests para el Motor de Decisión (Thresholding) — Tarea 3.5.1

Verifica:
- Clasificación correcta de ICD en zonas cognitivas
- Mapeo zona → estrategia pedagógica
- Comportamiento en los límites exactos de los umbrales (edge cases)
- Umbrales personalizados (ThresholdConfig)
- Manejo de valores None e inválidos

Uso:
    python -m pytest src/bio/test_decision.py -v
    python -m src.bio.test_decision  (script directo)
"""
from __future__ import annotations

import pytest

from src.bio.decision import (
    AIInteractionMode,
    CognitiveZone,
    PedagogicalStrategy,
    ThresholdConfig,
    classify_zone,
    get_all_strategies,
    get_strategy,
    get_strategy_for_record,
    get_threshold_ranges,
)
from src.bio.models import DifficultyEnum, TaskTypeEnum


# ============================================================================
# Tests de classify_zone
# ============================================================================

class TestClassifyZone:
    """Verifica la clasificación ICD → zona cognitiva."""

    def test_peak_zone(self) -> None:
        """ICD > 80 → PEAK."""
        assert classify_zone(81.0) == CognitiveZone.PEAK
        assert classify_zone(95.0) == CognitiveZone.PEAK
        assert classify_zone(100.0) == CognitiveZone.PEAK

    def test_normal_zone(self) -> None:
        """ICD entre 50 (excl) y 80 (incl) → NORMAL."""
        assert classify_zone(51.0) == CognitiveZone.NORMAL
        assert classify_zone(65.0) == CognitiveZone.NORMAL
        assert classify_zone(80.0) == CognitiveZone.NORMAL

    def test_fatigue_zone(self) -> None:
        """ICD entre 30 (excl) y 50 (incl) → FATIGUE."""
        assert classify_zone(31.0) == CognitiveZone.FATIGUE
        assert classify_zone(40.0) == CognitiveZone.FATIGUE
        assert classify_zone(50.0) == CognitiveZone.FATIGUE

    def test_burnout_zone(self) -> None:
        """ICD <= 30 → BURNOUT."""
        assert classify_zone(0.0) == CognitiveZone.BURNOUT
        assert classify_zone(15.0) == CognitiveZone.BURNOUT
        assert classify_zone(30.0) == CognitiveZone.BURNOUT

    def test_exact_boundaries(self) -> None:
        """Verifica comportamiento exacto en los umbrales (edge cases)."""
        # 80.0 es el techo de NORMAL → ICD=80 NO es PEAK
        assert classify_zone(80.0) == CognitiveZone.NORMAL
        assert classify_zone(80.01) == CognitiveZone.PEAK

        # 50.0 es el techo de FATIGUE → ICD=50 NO es NORMAL
        assert classify_zone(50.0) == CognitiveZone.FATIGUE
        assert classify_zone(50.01) == CognitiveZone.NORMAL

        # 30.0 es el techo de BURNOUT → ICD=30 NO es FATIGUE
        assert classify_zone(30.0) == CognitiveZone.BURNOUT
        assert classify_zone(30.01) == CognitiveZone.FATIGUE

    def test_extreme_values(self) -> None:
        """Verifica los extremos absolutos del rango."""
        assert classify_zone(0.0) == CognitiveZone.BURNOUT
        assert classify_zone(100.0) == CognitiveZone.PEAK

    def test_invalid_score_below_zero(self) -> None:
        """ICD negativo lanza ValueError."""
        with pytest.raises(ValueError, match="rango"):
            classify_zone(-1.0)

    def test_invalid_score_above_hundred(self) -> None:
        """ICD > 100 lanza ValueError."""
        with pytest.raises(ValueError, match="rango"):
            classify_zone(101.0)


# ============================================================================
# Tests de ThresholdConfig
# ============================================================================

class TestThresholdConfig:
    """Verifica la validación y personalización de umbrales."""

    def test_default_thresholds(self) -> None:
        """Los valores por defecto son 80, 50, 30."""
        config = ThresholdConfig()
        assert config.normal_ceil == 80.0
        assert config.fatigue_ceil == 50.0
        assert config.burnout_ceil == 30.0

    def test_custom_thresholds(self) -> None:
        """Umbrales personalizados se aplican correctamente."""
        config = ThresholdConfig(
            normal_ceil=70.0,
            fatigue_ceil=40.0,
            burnout_ceil=20.0,
        )
        # Con umbral ajustado, ICD=75 ahora es PEAK (antes era NORMAL)
        assert classify_zone(75.0, config) == CognitiveZone.PEAK
        # ICD=45 ahora es NORMAL (antes era FATIGUE)
        assert classify_zone(45.0, config) == CognitiveZone.NORMAL

    def test_invalid_thresholds_order(self) -> None:
        """Umbrales desordenados lanzan ValueError."""
        with pytest.raises(ValueError, match="umbrales"):
            ThresholdConfig(normal_ceil=30.0, fatigue_ceil=50.0, burnout_ceil=80.0)

    def test_invalid_thresholds_equal(self) -> None:
        """Umbrales iguales lanzan ValueError."""
        with pytest.raises(ValueError, match="umbrales"):
            ThresholdConfig(normal_ceil=50.0, fatigue_ceil=50.0, burnout_ceil=30.0)

    def test_invalid_thresholds_zero(self) -> None:
        """Burnout ceil en 0 lanza ValueError (debe ser > 0)."""
        with pytest.raises(ValueError, match="umbrales"):
            ThresholdConfig(normal_ceil=80.0, fatigue_ceil=50.0, burnout_ceil=0.0)


# ============================================================================
# Tests de get_strategy
# ============================================================================

class TestGetStrategy:
    """Verifica el mapeo ICD → estrategia pedagógica completa."""

    def test_peak_strategy(self) -> None:
        """ICD alto retorna Deep Work con modo Socrático."""
        strategy = get_strategy(90.0)
        assert strategy.zone == CognitiveZone.PEAK
        assert strategy.name == "Deep Work"
        assert strategy.ai_mode == AIInteractionMode.SOCRATIC
        assert strategy.max_difficulty == DifficultyEnum.EPIC
        assert TaskTypeEnum.MATH in strategy.recommended_tasks
        assert TaskTypeEnum.THEORY_NEW in strategy.recommended_tasks

    def test_normal_strategy(self) -> None:
        """ICD medio retorna Flow con modo Guided."""
        strategy = get_strategy(65.0)
        assert strategy.zone == CognitiveZone.NORMAL
        assert strategy.name == "Flow"
        assert strategy.ai_mode == AIInteractionMode.GUIDED
        assert strategy.max_difficulty == DifficultyEnum.HARD
        assert TaskTypeEnum.CODING in strategy.recommended_tasks

    def test_fatigue_strategy(self) -> None:
        """ICD bajo retorna Review con modo Supportive."""
        strategy = get_strategy(40.0)
        assert strategy.zone == CognitiveZone.FATIGUE
        assert strategy.name == "Review"
        assert strategy.ai_mode == AIInteractionMode.SUPPORTIVE
        assert strategy.max_difficulty == DifficultyEnum.MEDIUM
        assert TaskTypeEnum.REVIEW in strategy.recommended_tasks

    def test_burnout_strategy(self) -> None:
        """ICD muy bajo retorna Survival con modo Passive."""
        strategy = get_strategy(15.0)
        assert strategy.zone == CognitiveZone.BURNOUT
        assert strategy.name == "Survival"
        assert strategy.ai_mode == AIInteractionMode.PASSIVE
        assert strategy.max_difficulty == DifficultyEnum.EASY

    def test_strategy_has_prompt_hint(self) -> None:
        """Todas las estrategias incluyen un prompt_hint para el LLM."""
        for icd in [10.0, 40.0, 65.0, 90.0]:
            strategy = get_strategy(icd)
            assert strategy.prompt_hint, f"Falta prompt_hint para ICD={icd}"
            assert len(strategy.prompt_hint) > 20

    def test_strategy_has_color(self) -> None:
        """Todas las estrategias incluyen un color hex para la UI."""
        for icd in [10.0, 40.0, 65.0, 90.0]:
            strategy = get_strategy(icd)
            assert strategy.color.startswith("#")
            assert len(strategy.color) == 7  # formato #RRGGBB


# ============================================================================
# Tests de get_strategy_for_record (versión None-safe)
# ============================================================================

class TestGetStrategyForRecord:
    """Verifica la versión segura que acepta None."""

    def test_none_returns_none(self) -> None:
        """icd_score None retorna None."""
        assert get_strategy_for_record(None) is None

    def test_valid_score_returns_strategy(self) -> None:
        """icd_score válido retorna estrategia."""
        strategy = get_strategy_for_record(75.0)
        assert strategy is not None
        assert isinstance(strategy, PedagogicalStrategy)
        assert strategy.zone == CognitiveZone.NORMAL


# ============================================================================
# Tests de funciones auxiliares
# ============================================================================

class TestHelpers:
    """Verifica funciones auxiliares para la UI."""

    def test_get_all_strategies_returns_four(self) -> None:
        """get_all_strategies retorna exactamente 4 estrategias."""
        strategies = get_all_strategies()
        assert len(strategies) == 4

    def test_get_all_strategies_order(self) -> None:
        """Las estrategias están ordenadas de PEAK a BURNOUT."""
        strategies = get_all_strategies()
        zones = [s.zone for s in strategies]
        assert zones == [
            CognitiveZone.PEAK,
            CognitiveZone.NORMAL,
            CognitiveZone.FATIGUE,
            CognitiveZone.BURNOUT,
        ]

    def test_get_threshold_ranges_default(self) -> None:
        """Los rangos por defecto cubren todo [0, 100]."""
        ranges = get_threshold_ranges()
        assert len(ranges) == 4
        # Verificar que el rango completo está cubierto
        assert ranges[0] == (CognitiveZone.PEAK, 80.0, 100.0)
        assert ranges[1] == (CognitiveZone.NORMAL, 50.0, 80.0)
        assert ranges[2] == (CognitiveZone.FATIGUE, 30.0, 50.0)
        assert ranges[3] == (CognitiveZone.BURNOUT, 0.0, 30.0)

    def test_get_threshold_ranges_custom(self) -> None:
        """Los rangos se ajustan con umbrales personalizados."""
        config = ThresholdConfig(
            normal_ceil=75.0, fatigue_ceil=45.0, burnout_ceil=20.0
        )
        ranges = get_threshold_ranges(config)
        assert ranges[0] == (CognitiveZone.PEAK, 75.0, 100.0)
        assert ranges[1] == (CognitiveZone.NORMAL, 45.0, 75.0)
        assert ranges[3] == (CognitiveZone.BURNOUT, 0.0, 20.0)


# ============================================================================
# Script runner
# ============================================================================

def _run_demo() -> None:
    """Demo interactiva del motor de decisión."""
    print("=" * 70)
    print("Motor de Decisión — Demo")
    print("=" * 70)

    test_scores = [10.0, 25.0, 30.0, 40.0, 50.0, 65.0, 80.0, 85.0, 95.0]

    for score in test_scores:
        strategy = get_strategy(score)
        print(
            f"\n  ICD: {score:5.1f}  →  "
            f"{strategy.emoji} {strategy.name:<10s}  "
            f"(zona: {strategy.zone.value}, "
            f"IA: {strategy.ai_mode.value}, "
            f"max dificultad: {strategy.max_difficulty.value})"
        )
        print(f"              Tareas: {[t.value for t in strategy.recommended_tasks]}")

    print("\n" + "=" * 70)
    print("Rangos de umbrales (por defecto):")
    for zone, low, high in get_threshold_ranges():
        print(f"  {zone.value:>8s}: [{low:.0f}, {high:.0f}]")

    print("\n" + "=" * 70)
    print("Demo completada.")
    print("=" * 70)


if __name__ == "__main__":
    _run_demo()
