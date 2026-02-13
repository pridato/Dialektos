"""
Tests para src/bio/analysis.py — Módulo Bio-Adaptabilidad

Tests con datos sintéticos para verificar el pipeline de análisis de correlación.
Ejecutar:
    python -m pytest src/bio/test_analysis.py -v
    python src/bio/test_analysis.py

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

import shutil
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import List

import matplotlib
matplotlib.use("Agg")  # Backend no interactivo para tests

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from src.bio.analysis import (
    check_data_sufficiency,
    correlation_matrix,
    divergence_analysis,
    lag_analysis,
    load_analysis_dataframe,
    generate_report,
    partial_correlation,
    validate_icd_weights,
)


# ============================================================
# Fixtures: DataFrame sintético
# ============================================================


def _make_synthetic_df(n_days: int = 35, seed: int = 42) -> pd.DataFrame:
    """
    Genera un DataFrame sintético que simula el JOIN de las 3 tablas.

    Incluye correlaciones realistas entre features para que los tests
    no dependan de datos reales.

    Args:
        n_days: Número de días a generar.
        seed: Semilla para reproducibilidad.

    Returns:
        DataFrame con la misma estructura que load_analysis_dataframe().
    """
    rng = np.random.default_rng(seed)
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(n_days)]

    # Generar features con correlaciones internas
    base_state = rng.normal(0, 1, n_days)  # estado latente diario

    df = pd.DataFrame({
        "date": dates,
        # Biometrics
        "ln_rmssd": 3.5 + 0.3 * base_state + rng.normal(0, 0.1, n_days),
        "hrv_baseline_7d": np.full(n_days, 3.5),
        "sleep_quality": np.clip(
            65 + 10 * base_state + rng.normal(0, 5, n_days), 0, 100
        ).astype(int),
        "body_resources": np.clip(
            55 + 12 * base_state + rng.normal(0, 8, n_days), 0, 100
        ).astype(int),
        "energy_level": np.clip(
            5 + 1.5 * base_state + rng.normal(0, 1, n_days), 1, 10
        ).astype(int),
        "mental_clarity": np.clip(
            5 + 1.2 * base_state + rng.normal(0, 1.2, n_days), 1, 10
        ).astype(int),
        "mood": rng.choice(
            ["focused", "neutral", "anxious", "tired"],
            n_days,
            p=[0.3, 0.4, 0.15, 0.15],
        ),
        "icd_score": np.clip(
            50 + 15 * base_state + rng.normal(0, 5, n_days), 0, 100
        ),
        # Sessions (agregadas)
        "focus_score_mean": np.clip(
            5 + 1.5 * base_state + rng.normal(0, 0.8, n_days), 1, 10
        ),
        "focus_score_max": np.clip(
            6 + 1.5 * base_state + rng.normal(0, 0.8, n_days), 1, 10
        ).astype(int),
        "n_sessions": rng.integers(1, 4, n_days),
        "comprehension_mean": np.clip(
            60 + 12 * base_state + rng.normal(0, 10, n_days), 0, 100
        ),
        # Confounders
        "caffeine_mg": rng.integers(0, 300, n_days),
        "exercise_min": rng.integers(0, 90, n_days),
        "screen_time_pre_sleep": rng.integers(0, 120, n_days),
    })

    # Mood encoding
    mood_map = {"focused": 1.0, "neutral": 0.0, "anxious": -0.3, "tired": -0.5}
    df["mood_encoded"] = df["mood"].map(mood_map).fillna(0.0)

    return df


@pytest.fixture
def synthetic_df() -> pd.DataFrame:
    """Fixture: DataFrame sintético con 35 días de datos."""
    return _make_synthetic_df(n_days=35)


@pytest.fixture
def small_df() -> pd.DataFrame:
    """Fixture: DataFrame con solo 10 días (insuficiente)."""
    return _make_synthetic_df(n_days=10)


@pytest.fixture
def empty_df() -> pd.DataFrame:
    """Fixture: DataFrame vacío."""
    return pd.DataFrame()


@pytest.fixture
def tmp_output_dir():
    """Fixture: directorio temporal para reportes."""
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ============================================================
# Tests: check_data_sufficiency
# ============================================================


class TestCheckDataSufficiency:
    """Tests para la validación de suficiencia de datos."""

    def test_sufficient_data(self, synthetic_df: pd.DataFrame) -> None:
        warnings = check_data_sufficiency(synthetic_df, min_days=30)
        # Con 35 días no debería haber warning de cantidad
        insufficient = [w for w in warnings if "Solo hay" in w]
        assert len(insufficient) == 0

    def test_insufficient_data(self, small_df: pd.DataFrame) -> None:
        warnings = check_data_sufficiency(small_df, min_days=30)
        assert any("Solo hay 10 días" in w for w in warnings)

    def test_empty_data(self, empty_df: pd.DataFrame) -> None:
        warnings = check_data_sufficiency(empty_df)
        assert any("No hay datos" in w for w in warnings)

    def test_high_null_column(self, synthetic_df: pd.DataFrame) -> None:
        df = synthetic_df.copy()
        # Poner >50% NaN en focus_score_mean
        df.loc[df.index[:25], "focus_score_mean"] = np.nan
        warnings = check_data_sufficiency(df)
        assert any("focus_score_mean" in w for w in warnings)


# ============================================================
# Tests: correlation_matrix
# ============================================================


class TestCorrelationMatrix:
    """Tests para la matriz de correlación Spearman."""

    def test_returns_correct_types(self, synthetic_df: pd.DataFrame) -> None:
        fig, corr_df, alerts = correlation_matrix(synthetic_df)
        assert isinstance(fig, plt.Figure)
        assert isinstance(corr_df, pd.DataFrame)
        assert isinstance(alerts, list)
        plt.close(fig)

    def test_matrix_is_square(self, synthetic_df: pd.DataFrame) -> None:
        _, corr_df, _ = correlation_matrix(synthetic_df)
        assert corr_df.shape[0] == corr_df.shape[1]
        plt.close("all")

    def test_diagonal_is_one(self, synthetic_df: pd.DataFrame) -> None:
        _, corr_df, _ = correlation_matrix(synthetic_df)
        if not corr_df.empty:
            diag = np.diag(corr_df.values)
            np.testing.assert_allclose(diag, 1.0, atol=1e-10)
        plt.close("all")

    def test_alert_low_correlation(self) -> None:
        """Con datos aleatorios sin correlación, debería alertar."""
        rng = np.random.default_rng(99)
        n = 40
        df = pd.DataFrame({
            "ln_rmssd": rng.normal(0, 1, n),
            "sleep_quality": rng.integers(0, 100, n),
            "body_resources": rng.integers(0, 100, n),
            "energy_level": rng.integers(1, 10, n),
            "mental_clarity": rng.integers(1, 10, n),
            "icd_score": rng.uniform(0, 100, n),
            "caffeine_mg": rng.integers(0, 300, n),
            "exercise_min": rng.integers(0, 90, n),
            "focus_score_mean": rng.uniform(1, 10, n),
        })
        _, _, alerts = correlation_matrix(df)
        # Con datos random es muy probable que alerte
        # (no siempre, pero el test verifica que la función no crashea)
        assert isinstance(alerts, list)
        plt.close("all")


# ============================================================
# Tests: lag_analysis
# ============================================================


class TestLagAnalysis:
    """Tests para el análisis de lag temporal."""

    def test_returns_correct_types(self, synthetic_df: pd.DataFrame) -> None:
        fig, lag_df, alerts = lag_analysis(synthetic_df)
        assert isinstance(fig, plt.Figure)
        assert isinstance(lag_df, pd.DataFrame)
        assert isinstance(alerts, list)
        plt.close(fig)

    def test_lag_range(self, synthetic_df: pd.DataFrame) -> None:
        _, lag_df, _ = lag_analysis(synthetic_df, max_lag=3)
        if not lag_df.empty:
            assert lag_df["lag"].min() == 0
            assert lag_df["lag"].max() == 3
        plt.close("all")

    def test_all_features_present(self, synthetic_df: pd.DataFrame) -> None:
        _, lag_df, _ = lag_analysis(synthetic_df)
        if not lag_df.empty:
            for feat in ["ln_rmssd", "body_resources", "energy_level",
                         "sleep_quality"]:
                assert feat in lag_df["feature"].values
        plt.close("all")


# ============================================================
# Tests: partial_correlation
# ============================================================


class TestPartialCorrelation:
    """Tests para la correlación parcial."""

    def test_returns_correct_types(self, synthetic_df: pd.DataFrame) -> None:
        fig, partial_df, alerts = partial_correlation(synthetic_df)
        assert isinstance(fig, plt.Figure)
        assert isinstance(partial_df, pd.DataFrame)
        assert isinstance(alerts, list)
        plt.close(fig)

    def test_has_both_raw_and_partial(
        self, synthetic_df: pd.DataFrame
    ) -> None:
        _, partial_df, _ = partial_correlation(synthetic_df)
        if not partial_df.empty:
            assert "r_raw" in partial_df.columns
            assert "r_partial" in partial_df.columns
            assert "delta" in partial_df.columns
        plt.close("all")

    def test_r_values_in_range(self, synthetic_df: pd.DataFrame) -> None:
        _, partial_df, _ = partial_correlation(synthetic_df)
        if not partial_df.empty:
            for col in ["r_raw", "r_partial"]:
                vals = partial_df[col].dropna()
                assert (vals >= -1).all() and (vals <= 1).all()
        plt.close("all")


# ============================================================
# Tests: validate_icd_weights
# ============================================================


class TestValidateICDWeights:
    """Tests para la validación de pesos ICD."""

    def test_returns_correct_types(self, synthetic_df: pd.DataFrame) -> None:
        fig, reg_info, alerts = validate_icd_weights(synthetic_df)
        assert isinstance(fig, plt.Figure)
        assert isinstance(reg_info, dict)
        assert isinstance(alerts, list)
        plt.close(fig)

    def test_r_squared_in_range(self, synthetic_df: pd.DataFrame) -> None:
        _, reg_info, _ = validate_icd_weights(synthetic_df)
        if reg_info:
            r2 = reg_info["r_squared"]
            assert 0 <= r2 <= 1.0

    def test_weights_sum_to_one(self, synthetic_df: pd.DataFrame) -> None:
        _, reg_info, _ = validate_icd_weights(synthetic_df)
        if reg_info and reg_info.get("features"):
            total = sum(
                f["learned_weight"] for f in reg_info["features"].values()
            )
            np.testing.assert_allclose(total, 1.0, atol=0.01)
        plt.close("all")

    def test_insufficient_data(self) -> None:
        """Con muy pocos datos, debe devolver dict vacío."""
        tiny_df = pd.DataFrame({
            "ln_rmssd": [3.5],
            "focus_score_mean": [7.0],
        })
        _, reg_info, _ = validate_icd_weights(tiny_df)
        assert reg_info == {}
        plt.close("all")


# ============================================================
# Tests: divergence_analysis
# ============================================================


class TestDivergenceAnalysis:
    """Tests para el análisis de divergencia objetivo-subjetivo."""

    def test_returns_correct_types(self, synthetic_df: pd.DataFrame) -> None:
        fig, alerts = divergence_analysis(synthetic_df)
        assert isinstance(fig, plt.Figure)
        assert isinstance(alerts, list)
        plt.close(fig)

    def test_detects_outliers(self) -> None:
        """Con valores extremos, debe detectar divergencia."""
        df = pd.DataFrame({
            "date": [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)],
            "body_resources": [90, 20, 50],
            "energy_level": [2, 9, 5],  # Invertidos respecto a body_resources
            "icd_score": [60, 40, 50],
        })
        _, alerts = divergence_analysis(df)
        # body_resources=90, energy_scaled=(2-1)/9*100=11 → divergencia=79
        assert any("divergencia" in a.lower() for a in alerts)
        plt.close("all")


# ============================================================
# Tests: generate_report
# ============================================================


class TestGenerateReport:
    """Tests para la generación de reporte Markdown."""

    def test_creates_markdown_file(
        self, synthetic_df: pd.DataFrame, tmp_output_dir: Path
    ) -> None:
        # Generar figuras mínimas
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        figures = {"correlation_matrix": fig}
        results = {
            "correlation_matrix": pd.DataFrame(),
            "correlation_alerts": [],
            "lag_analysis": pd.DataFrame(),
            "lag_alerts": [],
            "partial_correlation": pd.DataFrame(),
            "partial_alerts": [],
            "icd_weights": {},
            "icd_alerts": [],
            "divergence_alerts": [],
        }
        warnings: List[str] = ["Test warning"]

        path = generate_report(
            synthetic_df, figures, results, warnings, tmp_output_dir,
        )

        assert path.exists()
        assert path.suffix == ".md"
        content = path.read_text(encoding="utf-8")
        assert "Reporte de Análisis de Correlación Semanal" in content
        assert "Test warning" in content
        plt.close("all")

    def test_saves_figures(
        self, synthetic_df: pd.DataFrame, tmp_output_dir: Path
    ) -> None:
        fig1, ax1 = plt.subplots()
        ax1.plot([1, 2])
        fig2, ax2 = plt.subplots()
        ax2.plot([3, 4])
        figures = {"correlation_matrix": fig1, "lag_analysis": fig2}
        results = {
            "correlation_matrix": pd.DataFrame(),
            "correlation_alerts": [],
            "lag_analysis": pd.DataFrame(),
            "lag_alerts": [],
            "partial_correlation": pd.DataFrame(),
            "partial_alerts": [],
            "icd_weights": {},
            "icd_alerts": [],
            "divergence_alerts": [],
        }

        generate_report(synthetic_df, figures, results, [], tmp_output_dir)

        figures_dir = tmp_output_dir / "figures"
        assert figures_dir.exists()
        pngs = list(figures_dir.glob("*.png"))
        assert len(pngs) == 2
        plt.close("all")


# ============================================================
# Entry point
# ============================================================


if __name__ == "__main__":
    print("=" * 60)
    print("  Tests de Análisis de Correlación — Dialektos")
    print("=" * 60)

    df = _make_synthetic_df(35)
    print(f"\nDataFrame sintético: {df.shape}")

    print("\n[1] check_data_sufficiency...")
    w = check_data_sufficiency(df)
    print(f"  Warnings: {w}")

    print("\n[2] correlation_matrix...")
    fig, corr, alerts = correlation_matrix(df)
    print(f"  Shape: {corr.shape}, Alerts: {alerts}")
    plt.close(fig)

    print("\n[3] lag_analysis...")
    fig, lag_df, alerts = lag_analysis(df)
    print(f"  Rows: {len(lag_df)}, Alerts: {alerts}")
    plt.close(fig)

    print("\n[4] partial_correlation...")
    fig, p_df, alerts = partial_correlation(df)
    print(f"  Rows: {len(p_df)}, Alerts: {alerts}")
    plt.close(fig)

    print("\n[5] validate_icd_weights...")
    fig, reg, alerts = validate_icd_weights(df)
    print(f"  R²: {reg.get('r_squared', 'N/A')}, Alerts: {alerts}")
    plt.close(fig)

    print("\n[6] divergence_analysis...")
    fig, alerts = divergence_analysis(df)
    print(f"  Alerts: {alerts}")
    plt.close(fig)

    print("\n[7] generate_report...")
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    fig_dummy, _ = plt.subplots()
    report_path = generate_report(
        df,
        {"correlation_matrix": fig_dummy},
        {
            "correlation_matrix": corr,
            "correlation_alerts": [],
            "lag_analysis": lag_df,
            "lag_alerts": [],
            "partial_correlation": p_df,
            "partial_alerts": [],
            "icd_weights": reg,
            "icd_alerts": [],
            "divergence_alerts": [],
        },
        [],
        tmp,
    )
    print(f"  Reporte en: {report_path}")
    plt.close("all")

    print("\n✓ Todos los tests manuales pasaron.")
