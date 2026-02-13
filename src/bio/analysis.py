"""
Análisis de Correlación Semanal — Módulo Bio-Adaptabilidad

Script que genera un reporte Markdown con:
1. Matriz de correlación (Spearman) entre features y focus_score
2. Detección de lag temporal (shift 1-3 días)
3. Correlación parcial controlando confounders
4. Validación de pesos ICD vs regresión múltiple
5. Divergencia objetivo-subjetivo (body_resources vs energy_level)

Ejecutar:
    python -m src.bio.analysis
    python -m src.bio.analysis --db data/metrics.db

Referencia: docs/TAREAS.md § 3.7.1

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from sqlmodel import Session, select

# Import opcional de pingouin para correlación parcial
try:
    import pingouin as pg
    HAS_PINGOUIN = True
except ImportError:
    HAS_PINGOUIN = False
    pg = None

from src.bio.db import get_engine
from src.bio.models import DailyBiometrics, DailyConfounders, StudySession

# ============================================================
# Constantes de estilo (reutilizadas del dashboard ICD)
# ============================================================
_STYLE: Dict[str, Any] = {
    "figure.facecolor": "#0e1117",
    "axes.facecolor": "#0e1117",
    "axes.edgecolor": "#3a3f4b",
    "axes.labelcolor": "#c9d1d9",
    "text.color": "#c9d1d9",
    "xtick.color": "#8b949e",
    "ytick.color": "#8b949e",
    "grid.color": "#21262d",
    "grid.alpha": 0.6,
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
}

C_ACCENT: str = "#58a6ff"
C_GREEN: str = "#3fb950"
C_YELLOW: str = "#d29922"
C_ORANGE: str = "#db6d28"
C_RED: str = "#f85149"
C_PURPLE: str = "#bc8cff"
C_CYAN: str = "#39d2c0"
C_GRAY: str = "#8b949e"

# Pesos manuales del ICD definidos en src/bio/metrics.py § calculate_icd
ICD_MANUAL_WEIGHTS: Dict[str, float] = {
    "ln_rmssd": 0.25,
    "sleep_quality": 0.20,
    "body_resources": 0.20,
    "energy_level": 0.15,
    "mental_clarity": 0.10,
    "mood_encoded": 0.10,
}

# Features principales para los análisis
ANALYSIS_FEATURES: List[str] = [
    "ln_rmssd",
    "sleep_quality",
    "body_resources",
    "energy_level",
    "mental_clarity",
    "icd_score",
    "caffeine_mg",
    "exercise_min",
]

# Features biométricas clave para lag analysis
LAG_FEATURES: List[str] = [
    "ln_rmssd",
    "body_resources",
    "energy_level",
    "sleep_quality",
]

# Features para correlación parcial
PARTIAL_FEATURES: List[str] = [
    "ln_rmssd",
    "body_resources",
    "energy_level",
    "sleep_quality",
]

# Covariates (confounders) a controlar
DEFAULT_COVARIATES: List[str] = ["caffeine_mg", "exercise_min"]

# Codificación de mood para regresión
MOOD_ENCODING: Dict[str, float] = {
    "focused": 1.0,
    "neutral": 0.0,
    "anxious": -0.3,
    "tired": -0.5,
}


def _apply_style() -> None:
    """Aplica la paleta oscura consistente con el dashboard ICD."""
    plt.rcParams.update(_STYLE)


# ============================================================
# 1. Carga de datos
# ============================================================


def load_analysis_dataframe(
    engine: Any,
) -> pd.DataFrame:
    """
    Carga y une las tres tablas (biometrics, sessions, confounders) en un
    DataFrame unificado con una fila por día.

    StudySession se agrega por día: focus_score_mean, focus_score_max, n_sessions.

    Args:
        engine: Motor SQLAlchemy conectado a metrics.db.

    Returns:
        DataFrame con columnas de las tres tablas, indexado por date.
    """
    with Session(engine) as session:
        # --- DailyBiometrics ---
        bio_rows = session.exec(
            select(DailyBiometrics).order_by(DailyBiometrics.date.asc())
        ).all()
        bio_df = pd.DataFrame([row.model_dump() for row in bio_rows])

        # --- StudySession (agregar por día) ---
        ss_rows = session.exec(
            select(StudySession).order_by(StudySession.date.asc())
        ).all()
        if ss_rows:
            ss_df = pd.DataFrame([row.model_dump() for row in ss_rows])
            ss_agg = (
                ss_df.groupby("date")
                .agg(
                    focus_score_mean=("focus_score", "mean"),
                    focus_score_max=("focus_score", "max"),
                    n_sessions=("session_id", "count"),
                    comprehension_mean=("comprehension_rate", "mean"),
                )
                .reset_index()
            )
        else:
            ss_agg = pd.DataFrame(
                columns=["date", "focus_score_mean", "focus_score_max",
                          "n_sessions", "comprehension_mean"]
            )

        # --- DailyConfounders ---
        conf_rows = session.exec(
            select(DailyConfounders).order_by(DailyConfounders.date.asc())
        ).all()
        if conf_rows:
            conf_df = pd.DataFrame([row.model_dump() for row in conf_rows])
        else:
            conf_df = pd.DataFrame(columns=["date"])

    # --- Merge ---
    if bio_df.empty:
        return pd.DataFrame()

    df = bio_df.merge(ss_agg, on="date", how="left")
    if not conf_df.empty:
        df = df.merge(conf_df, on="date", how="left", suffixes=("", "_conf"))

    # Codificar mood como numérico
    df["mood_encoded"] = df["mood"].map(MOOD_ENCODING).fillna(0.0)

    df = df.sort_values("date").reset_index(drop=True)
    return df


# ============================================================
# 2. Validación de datos
# ============================================================


def check_data_sufficiency(
    df: pd.DataFrame,
    min_days: int = 30,
) -> List[str]:
    """
    Verifica si hay suficientes datos para un análisis significativo.

    Args:
        df: DataFrame unificado (una fila por día).
        min_days: Mínimo de días requerido.

    Returns:
        Lista de strings con advertencias (vacía si todo OK).
    """
    warnings: List[str] = []

    n_days = len(df)
    if n_days == 0:
        warnings.append("No hay datos en la base de datos.")
        return warnings

    if n_days < min_days:
        warnings.append(
            f"Solo hay {n_days} días de datos (mínimo recomendado: {min_days}). "
            "Las correlaciones pueden no ser significativas."
        )

    # Columnas con >50 % NaN
    focus_cols = ["focus_score_mean"]
    for col in ANALYSIS_FEATURES + focus_cols:
        if col in df.columns:
            pct_null = df[col].isna().mean()
            if pct_null > 0.50:
                warnings.append(
                    f"Columna '{col}' tiene {pct_null:.0%} valores nulos — "
                    "resultados poco fiables."
                )

    # Sin sesiones de estudio registradas
    if "focus_score_mean" in df.columns and df["focus_score_mean"].dropna().empty:
        warnings.append(
            "No hay sesiones de estudio registradas (focus_score). "
            "Los análisis de correlación con rendimiento no son posibles."
        )

    return warnings


# ============================================================
# 3. Matriz de correlación
# ============================================================


def correlation_matrix(
    df: pd.DataFrame,
    target: str = "focus_score_mean",
) -> Tuple[plt.Figure, pd.DataFrame, List[str]]:
    """
    Calcula la matriz de correlación de Spearman entre features y el target.

    Spearman es robusto con muestras pequeñas y relaciones no lineales.

    Args:
        df: DataFrame unificado.
        target: Variable objetivo (por defecto, focus_score promedio diario).

    Returns:
        (figura del heatmap, DataFrame de correlaciones, lista de alertas)
    """
    _apply_style()
    alerts: List[str] = []

    cols = [c for c in ANALYSIS_FEATURES + [target] if c in df.columns]
    subset = df[cols].dropna()

    if len(subset) < 5:
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(
            0.5, 0.5, "Datos insuficientes para\ncalcular correlaciones",
            ha="center", va="center", fontsize=14, color=C_RED,
        )
        ax.set_axis_off()
        return fig, pd.DataFrame(), alerts

    corr = subset.corr(method="spearman")

    # Alerta si correlaciones con target son todas < 0.3
    if target in corr.columns:
        target_corrs = corr[target].drop(target, errors="ignore").abs()
        if (target_corrs < 0.3).all():
            alerts.append(
                f"Ninguna feature tiene |r| >= 0.3 con '{target}'. "
                "Correlaciones insuficientes para conclusiones."
            )

    # --- Heatmap ---
    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    cmap = sns.diverging_palette(250, 15, s=75, l=40, as_cmap=True)

    sns.heatmap(
        corr,
        mask=mask,
        annot=True,
        fmt=".2f",
        cmap=cmap,
        center=0,
        vmin=-1,
        vmax=1,
        linewidths=0.5,
        linecolor="#21262d",
        cbar_kws={"shrink": 0.8, "label": "Spearman ρ"},
        ax=ax,
    )
    ax.set_title("Matriz de Correlación (Spearman)", pad=15)
    fig.tight_layout()

    return fig, corr, alerts


# ============================================================
# 4. Detección de lag
# ============================================================


def lag_analysis(
    df: pd.DataFrame,
    target: str = "focus_score_mean",
    max_lag: int = 3,
) -> Tuple[plt.Figure, pd.DataFrame, List[str]]:
    """
    Analiza si las métricas de días previos (lag 0-3) correlacionan
    con el focus_score actual.

    Permite descubrir, por ejemplo, que el sueño de *anteayer* influye
    más en el rendimiento de hoy que el de ayer.

    Args:
        df: DataFrame unificado (ordenado por date).
        target: Variable objetivo.
        max_lag: Máximo número de días de retardo a evaluar.

    Returns:
        (figura, DataFrame con coeficientes por feature/lag, alertas)
    """
    _apply_style()
    alerts: List[str] = []

    features = [f for f in LAG_FEATURES if f in df.columns]
    if target not in df.columns or not features:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Datos insuficientes para lag analysis",
                ha="center", va="center", color=C_RED)
        ax.set_axis_off()
        return fig, pd.DataFrame(), alerts

    results: List[Dict[str, Any]] = []
    for feat in features:
        for lag in range(0, max_lag + 1):
            shifted = df[feat].shift(lag)
            valid = pd.DataFrame({"x": shifted, "y": df[target]}).dropna()
            if len(valid) >= 5:
                rho, pval = stats.spearmanr(valid["x"], valid["y"])
            else:
                rho, pval = np.nan, np.nan
            results.append({
                "feature": feat,
                "lag": lag,
                "spearman_r": rho,
                "p_value": pval,
            })

    lag_df = pd.DataFrame(results)

    # Mejor lag por feature
    best_rows = []
    for feat in features:
        sub = lag_df[lag_df["feature"] == feat].dropna(subset=["spearman_r"])
        if not sub.empty:
            best_idx = sub["spearman_r"].abs().idxmax()
            best = sub.loc[best_idx]
            best_rows.append(best)
            if best["lag"] > 0:
                alerts.append(
                    f"'{feat}' tiene mayor correlación con lag={int(best['lag'])} días "
                    f"(r={best['spearman_r']:.2f})."
                )

    # --- Gráfico de barras agrupadas ---
    fig, ax = plt.subplots(figsize=(10, 6))
    n_features = len(features)
    n_lags = max_lag + 1
    x = np.arange(n_features)
    width = 0.8 / n_lags
    lag_colors = [C_ACCENT, C_GREEN, C_YELLOW, C_ORANGE]

    for i in range(n_lags):
        vals = []
        for feat in features:
            row = lag_df[(lag_df["feature"] == feat) & (lag_df["lag"] == i)]
            vals.append(row["spearman_r"].values[0] if len(row) else 0.0)
        offset = (i - n_lags / 2 + 0.5) * width
        bars = ax.bar(
            x + offset, vals, width,
            label=f"Lag {i}d", color=lag_colors[i % len(lag_colors)], alpha=0.85,
        )
        # Anotar valores
        for bar, v in zip(bars, vals):
            if not np.isnan(v):
                ax.text(
                    bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{v:.2f}", ha="center", va="bottom", fontsize=8,
                    color="#c9d1d9",
                )

    ax.set_xticks(x)
    ax.set_xticklabels(features, rotation=25, ha="right")
    ax.set_ylabel("Spearman ρ")
    ax.set_title(f"Correlación con {target} por Lag Temporal", pad=12)
    ax.legend(loc="upper right", framealpha=0.7)
    ax.axhline(0, color=C_GRAY, linewidth=0.8, linestyle="--")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    return fig, lag_df, alerts


# ============================================================
# 5. Correlación parcial
# ============================================================


def partial_correlation(
    df: pd.DataFrame,
    target: str = "focus_score_mean",
    covariates: Optional[List[str]] = None,
) -> Tuple[plt.Figure, pd.DataFrame, List[str]]:
    """
    Calcula correlaciones parciales controlando confounders (cafeína, ejercicio).

    Permite aislar el efecto *real* de cada feature sobre el rendimiento,
    eliminando la influencia de variables de confusión.

    Usa pingouin.partial_corr() internamente.

    Args:
        df: DataFrame unificado.
        target: Variable objetivo.
        covariates: Variables a controlar. Por defecto: caffeine_mg, exercise_min.

    Returns:
        (figura, DataFrame comparativo bruta vs parcial, alertas)
    """
    _apply_style()
    alerts: List[str] = []

    if covariates is None:
        covariates = DEFAULT_COVARIATES

    features = [f for f in PARTIAL_FEATURES if f in df.columns]
    covar_present = [c for c in covariates if c in df.columns]

    if target not in df.columns or not features:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Datos insuficientes para\ncorrelación parcial",
                ha="center", va="center", color=C_RED)
        ax.set_axis_off()
        return fig, pd.DataFrame(), alerts

    rows: List[Dict[str, Any]] = []
    for feat in features:
        needed = [feat, target] + covar_present
        sub = df[needed].dropna()

        # Correlación bruta (Spearman)
        if len(sub) >= 5:
            rho_raw, p_raw = stats.spearmanr(sub[feat], sub[target])
        else:
            rho_raw, p_raw = np.nan, np.nan

        # Correlación parcial
        if len(sub) >= 5 and covar_present:
            if HAS_PINGOUIN and pg is not None:
                try:
                    result = pg.partial_corr(
                        data=sub, x=feat, y=target, covar=covar_present,
                        method="spearman",
                    )
                    rho_partial = result["r"].values[0]
                    p_partial = result["p-val"].values[0]
                except Exception:
                    rho_partial, p_partial = np.nan, np.nan
            else:
                # Si pingouin no está disponible, usar correlación bruta
                # y mostrar advertencia solo una vez
                if not hasattr(partial_correlation, '_warned'):
                    alerts.append(
                        "⚠️ pingouin no disponible: usando correlación bruta "
                        "en lugar de parcial. Instala con: pip install pingouin"
                    )
                    partial_correlation._warned = True
                rho_partial, p_partial = rho_raw, p_raw
        else:
            rho_partial, p_partial = rho_raw, p_raw

        rows.append({
            "feature": feat,
            "r_raw": rho_raw,
            "p_raw": p_raw,
            "r_partial": rho_partial,
            "p_partial": p_partial,
            "delta": (rho_partial - rho_raw) if not (
                np.isnan(rho_partial) or np.isnan(rho_raw)
            ) else np.nan,
        })

    partial_df = pd.DataFrame(rows)

    # Alertas sobre confounders significativos
    for _, row in partial_df.iterrows():
        if not np.isnan(row["delta"]) and abs(row["delta"]) > 0.15:
            direction = "infla" if row["delta"] < 0 else "suprime"
            alerts.append(
                f"Los confounders {direction}n la correlación de "
                f"'{row['feature']}' en {abs(row['delta']):.2f} puntos."
            )

    # --- Barplot pareado ---
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(features))
    width = 0.35

    vals_raw = partial_df["r_raw"].values
    vals_partial = partial_df["r_partial"].values

    ax.bar(x - width / 2, vals_raw, width, label="Correlación bruta",
           color=C_GRAY, alpha=0.7)
    ax.bar(x + width / 2, vals_partial, width, label="Correlación parcial",
           color=C_ACCENT, alpha=0.85)

    # Anotar valores
    for i, (vr, vp) in enumerate(zip(vals_raw, vals_partial)):
        if not np.isnan(vr):
            ax.text(i - width / 2, vr, f"{vr:.2f}", ha="center",
                    va="bottom" if vr >= 0 else "top", fontsize=9,
                    color="#c9d1d9")
        if not np.isnan(vp):
            ax.text(i + width / 2, vp, f"{vp:.2f}", ha="center",
                    va="bottom" if vp >= 0 else "top", fontsize=9,
                    color="#c9d1d9")

    ax.set_xticks(x)
    ax.set_xticklabels(features, rotation=25, ha="right")
    ax.set_ylabel("Spearman ρ")
    ax.set_title(
        f"Correlación Bruta vs Parcial (controlando {', '.join(covar_present)})",
        pad=12,
    )
    ax.legend(loc="upper right", framealpha=0.7)
    ax.axhline(0, color=C_GRAY, linewidth=0.8, linestyle="--")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    return fig, partial_df, alerts


# ============================================================
# 6. Validación de pesos ICD
# ============================================================


def validate_icd_weights(
    df: pd.DataFrame,
) -> Tuple[plt.Figure, Dict[str, Any], List[str]]:
    """
    Regresión múltiple: focus_score_mean ~ features del ICD.

    Compara los coeficientes aprendidos por OLS con los pesos manuales
    de la fórmula ICD actual (definidos en src/bio/metrics.py).

    Implementación con numpy.linalg.lstsq para evitar dependencias extra.

    Args:
        df: DataFrame unificado.

    Returns:
        (figura, dict con resultados de regresión, alertas)
    """
    _apply_style()
    alerts: List[str] = []

    regression_features = [
        "ln_rmssd", "sleep_quality", "body_resources",
        "energy_level", "mental_clarity", "mood_encoded",
    ]
    target = "focus_score_mean"

    available = [f for f in regression_features if f in df.columns]
    if target not in df.columns or len(available) < 3:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Datos insuficientes para\nregresión OLS",
                ha="center", va="center", color=C_RED)
        ax.set_axis_off()
        return fig, {}, alerts

    subset = df[available + [target]].dropna()

    if len(subset) < len(available) + 2:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Datos insuficientes para\nregresión OLS",
                ha="center", va="center", color=C_RED)
        ax.set_axis_off()
        return fig, {}, alerts

    # --- Normalizar features a 0-1 para comparabilidad con pesos ICD ---
    X_raw = subset[available].values.astype(float)
    y = subset[target].values.astype(float)

    # Min-max scaling por columna
    x_min = X_raw.min(axis=0)
    x_max = X_raw.max(axis=0)
    x_range = x_max - x_min
    x_range[x_range == 0] = 1.0  # evitar división por 0
    X_norm = (X_raw - x_min) / x_range

    # Añadir intercept
    X_design = np.column_stack([np.ones(len(X_norm)), X_norm])

    # OLS via least squares
    result, residuals, rank, sv = np.linalg.lstsq(X_design, y, rcond=None)

    intercept = result[0]
    coefs = result[1:]

    # R²
    y_pred = X_design @ result
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Normalizar coeficientes a pesos relativos (sumando a 1)
    abs_coefs = np.abs(coefs)
    total_abs = abs_coefs.sum()
    if total_abs > 0:
        learned_weights = abs_coefs / total_abs
    else:
        learned_weights = np.zeros_like(coefs)

    # Construir resultado
    reg_results: Dict[str, Any] = {
        "intercept": float(intercept),
        "r_squared": float(r_squared),
        "n_observations": len(subset),
        "features": {},
    }

    for i, feat in enumerate(available):
        manual_w = ICD_MANUAL_WEIGHTS.get(feat, 0.0)
        reg_results["features"][feat] = {
            "coefficient": float(coefs[i]),
            "learned_weight": float(learned_weights[i]),
            "manual_weight": manual_w,
        }

    # Alertas
    if r_squared < 0.3:
        alerts.append(
            f"R² = {r_squared:.2f} — el modelo lineal explica poca varianza. "
            "Las relaciones pueden ser no lineales."
        )

    # Detectar discrepancias grandes entre pesos
    for feat in available:
        info = reg_results["features"][feat]
        diff = abs(info["learned_weight"] - info["manual_weight"])
        if diff > 0.15:
            alerts.append(
                f"Discrepancia en '{feat}': peso manual={info['manual_weight']:.2f}, "
                f"peso aprendido={info['learned_weight']:.2f} (Δ={diff:.2f})."
            )

    # --- Barplot comparativo ---
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(available))
    width = 0.35

    manual_vals = [ICD_MANUAL_WEIGHTS.get(f, 0.0) for f in available]
    learned_vals = [float(learned_weights[i]) for i in range(len(available))]

    ax.bar(x - width / 2, manual_vals, width,
           label="Pesos manuales (ICD)", color=C_PURPLE, alpha=0.8)
    ax.bar(x + width / 2, learned_vals, width,
           label=f"Pesos aprendidos (R²={r_squared:.2f})", color=C_GREEN, alpha=0.8)

    for i, (vm, vl) in enumerate(zip(manual_vals, learned_vals)):
        ax.text(i - width / 2, vm, f"{vm:.2f}", ha="center", va="bottom",
                fontsize=9, color="#c9d1d9")
        ax.text(i + width / 2, vl, f"{vl:.2f}", ha="center", va="bottom",
                fontsize=9, color="#c9d1d9")

    ax.set_xticks(x)
    ax.set_xticklabels(available, rotation=25, ha="right")
    ax.set_ylabel("Peso relativo")
    ax.set_title("Pesos ICD Manuales vs Aprendidos (OLS)", pad=12)
    ax.legend(loc="upper right", framealpha=0.7)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    return fig, reg_results, alerts


# ============================================================
# 7. Divergencia objetivo-subjetivo
# ============================================================


def divergence_analysis(
    df: pd.DataFrame,
) -> Tuple[plt.Figure, List[str]]:
    """
    Scatter plot de body_resources (objetivo, 0-100) vs energy_level
    (subjetivo, escalado a 0-100), coloreado por icd_score.

    Identifica días donde biología y percepción divergen significativamente.

    Args:
        df: DataFrame unificado.

    Returns:
        (figura del scatter, alertas sobre outliers)
    """
    _apply_style()
    alerts: List[str] = []

    needed = ["body_resources", "energy_level", "icd_score", "date"]
    available = [c for c in needed if c in df.columns]
    if "body_resources" not in available or "energy_level" not in available:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Faltan columnas para\ndivergencia analysis",
                ha="center", va="center", color=C_RED)
        ax.set_axis_off()
        return fig, alerts

    sub = df[available].dropna(subset=["body_resources", "energy_level"])
    if sub.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Sin datos válidos", ha="center", va="center",
                color=C_RED)
        ax.set_axis_off()
        return fig, alerts

    # Escalar energy_level (1-10) a 0-100
    sub = sub.copy()
    sub["energy_scaled"] = ((sub["energy_level"] - 1) / 9) * 100

    # Divergencia absoluta
    sub["divergence"] = (sub["body_resources"] - sub["energy_scaled"]).abs()

    fig, ax = plt.subplots(figsize=(9, 7))

    # Scatter coloreado por ICD
    has_icd = "icd_score" in sub.columns and sub["icd_score"].notna().any()
    if has_icd:
        scatter = ax.scatter(
            sub["body_resources"], sub["energy_scaled"],
            c=sub["icd_score"], cmap="RdYlGn", s=60, alpha=0.8,
            edgecolors="#3a3f4b", linewidths=0.5, vmin=0, vmax=100,
        )
        cbar = fig.colorbar(scatter, ax=ax, shrink=0.8, pad=0.02)
        cbar.set_label("ICD Score", fontsize=10)
    else:
        ax.scatter(
            sub["body_resources"], sub["energy_scaled"],
            c=C_ACCENT, s=60, alpha=0.8,
            edgecolors="#3a3f4b", linewidths=0.5,
        )

    # Línea de concordancia perfecta
    ax.plot([0, 100], [0, 100], "--", color=C_GRAY, linewidth=1, alpha=0.6,
            label="Concordancia perfecta")

    # Anotar outliers (divergencia > 25 puntos)
    outliers = sub[sub["divergence"] > 25]
    n_outliers = len(outliers)
    if n_outliers > 0:
        for _, row in outliers.iterrows():
            label = str(row["date"]) if "date" in row.index else ""
            ax.annotate(
                label,
                xy=(row["body_resources"], row["energy_scaled"]),
                xytext=(5, 5), textcoords="offset points",
                fontsize=7, color=C_RED, alpha=0.9,
            )
        pct = n_outliers / len(sub) * 100
        alerts.append(
            f"{n_outliers} días ({pct:.0f}%) con divergencia objetivo-subjetivo > 25 puntos."
        )

    ax.set_xlabel("Body Resources (objetivo, 0-100)")
    ax.set_ylabel("Energy Level escalado (subjetivo, 0-100)")
    ax.set_title("Divergencia Objetivo vs Subjetivo", pad=12)
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
    ax.legend(loc="upper left", framealpha=0.7)
    ax.grid(alpha=0.3)
    fig.tight_layout()

    return fig, alerts


# ============================================================
# 8. Generación de reporte Markdown
# ============================================================


def generate_report(
    df: pd.DataFrame,
    figures: Dict[str, plt.Figure],
    results: Dict[str, Any],
    warnings: List[str],
    output_dir: Path,
) -> Path:
    """
    Genera un reporte Markdown con gráficos embebidos y tablas de coeficientes.

    Args:
        df: DataFrame unificado (para metadatos).
        figures: Dict nombre → Figure de matplotlib.
        results: Dict con DataFrames y dicts de resultados por análisis.
        warnings: Lista de advertencias del check de suficiencia.
        output_dir: Directorio base para guardar reporte y figuras.

    Returns:
        Path al archivo .md generado.
    """
    timestamp = datetime.now().strftime("%Y%m%d")
    report_name = f"weekly_analysis_{timestamp}.md"
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Guardar figuras como PNG
    saved_figures: Dict[str, str] = {}
    for name, fig in figures.items():
        fname = f"{name}_{timestamp}.png"
        fpath = figures_dir / fname
        fig.savefig(fpath, dpi=150, bbox_inches="tight", facecolor="#0e1117")
        plt.close(fig)
        saved_figures[name] = f"figures/{fname}"

    # --- Construir Markdown ---
    lines: List[str] = []

    # Header
    date_min = df["date"].min() if not df.empty else "N/A"
    date_max = df["date"].max() if not df.empty else "N/A"
    n_days = len(df)

    lines.append("# Reporte de Análisis de Correlación Semanal")
    lines.append("")
    lines.append(f"**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Rango de datos:** {date_min} → {date_max} ({n_days} días)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Warnings
    if warnings:
        lines.append("## Advertencias")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 1. Matriz de correlación
    lines.append("## 1. Matriz de Correlación (Spearman)")
    lines.append("")
    if "correlation_matrix" in saved_figures:
        lines.append(f"![Matriz de Correlación]({saved_figures['correlation_matrix']})")
        lines.append("")
    corr_df: pd.DataFrame = results.get("correlation_matrix", pd.DataFrame())
    if not corr_df.empty and "focus_score_mean" in corr_df.columns:
        lines.append("### Correlaciones con focus_score_mean")
        lines.append("")
        lines.append("| Feature | Spearman ρ |")
        lines.append("|---------|-----------|")
        target_corrs = corr_df["focus_score_mean"].drop(
            "focus_score_mean", errors="ignore"
        ).sort_values(ascending=False)
        for feat, val in target_corrs.items():
            lines.append(f"| {feat} | {val:.3f} |")
        lines.append("")
    corr_alerts: List[str] = results.get("correlation_alerts", [])
    for a in corr_alerts:
        lines.append(f"> **Alerta:** {a}")
        lines.append("")
    lines.append("---")
    lines.append("")

    # 2. Lag analysis
    lines.append("## 2. Análisis de Lag Temporal")
    lines.append("")
    if "lag_analysis" in saved_figures:
        lines.append(f"![Lag Analysis]({saved_figures['lag_analysis']})")
        lines.append("")
    lag_df: pd.DataFrame = results.get("lag_analysis", pd.DataFrame())
    if not lag_df.empty:
        lines.append("### Coeficientes por Feature y Lag")
        lines.append("")
        lines.append("| Feature | Lag 0 | Lag 1 | Lag 2 | Lag 3 |")
        lines.append("|---------|-------|-------|-------|-------|")
        for feat in lag_df["feature"].unique():
            row_data = lag_df[lag_df["feature"] == feat]
            vals = []
            for lag in range(4):
                r = row_data[row_data["lag"] == lag]["spearman_r"]
                if len(r) and not np.isnan(r.values[0]):
                    vals.append(f"{r.values[0]:.3f}")
                else:
                    vals.append("—")
            lines.append(f"| {feat} | {' | '.join(vals)} |")
        lines.append("")
    lag_alerts: List[str] = results.get("lag_alerts", [])
    for a in lag_alerts:
        lines.append(f"> **Hallazgo:** {a}")
        lines.append("")
    lines.append("---")
    lines.append("")

    # 3. Correlación parcial
    lines.append("## 3. Correlación Parcial (controlando confounders)")
    lines.append("")
    if "partial_correlation" in saved_figures:
        lines.append(
            f"![Correlación Parcial]({saved_figures['partial_correlation']})"
        )
        lines.append("")
    partial_df: pd.DataFrame = results.get("partial_correlation", pd.DataFrame())
    if not partial_df.empty:
        lines.append("### Bruta vs Parcial")
        lines.append("")
        lines.append("| Feature | r bruta | r parcial | Δ |")
        lines.append("|---------|---------|-----------|---|")
        for _, row in partial_df.iterrows():
            r_raw_str = f"{row['r_raw']:.3f}" if not np.isnan(
                row["r_raw"]) else "—"
            r_part_str = f"{row['r_partial']:.3f}" if not np.isnan(
                row["r_partial"]) else "—"
            delta_str = f"{row['delta']:.3f}" if not np.isnan(
                row["delta"]) else "—"
            lines.append(
                f"| {row['feature']} | {r_raw_str} | "
                f"{r_part_str} | {delta_str} |"
            )
        lines.append("")
    partial_alerts: List[str] = results.get("partial_alerts", [])
    for a in partial_alerts:
        lines.append(f"> **Hallazgo:** {a}")
        lines.append("")
    lines.append("---")
    lines.append("")

    # 4. Validación de pesos ICD
    lines.append("## 4. Validación de Pesos ICD (Regresión OLS)")
    lines.append("")
    if "icd_weights" in saved_figures:
        lines.append(f"![Pesos ICD]({saved_figures['icd_weights']})")
        lines.append("")
    reg_info: Dict[str, Any] = results.get("icd_weights", {})
    if reg_info:
        lines.append(f"**R² = {reg_info.get('r_squared', 0):.3f}** "
                      f"(n = {reg_info.get('n_observations', 0)})")
        lines.append("")
        lines.append("| Feature | Peso manual | Peso aprendido | Δ |")
        lines.append("|---------|-------------|----------------|---|")
        for feat, info in reg_info.get("features", {}).items():
            diff = abs(info["learned_weight"] - info["manual_weight"])
            lines.append(
                f"| {feat} | {info['manual_weight']:.2f} | "
                f"{info['learned_weight']:.2f} | {diff:.2f} |"
            )
        lines.append("")
    reg_alerts: List[str] = results.get("icd_alerts", [])
    for a in reg_alerts:
        lines.append(f"> **Alerta:** {a}")
        lines.append("")
    lines.append("---")
    lines.append("")

    # 5. Divergencia
    lines.append("## 5. Divergencia Objetivo vs Subjetivo")
    lines.append("")
    if "divergence" in saved_figures:
        lines.append(f"![Divergencia]({saved_figures['divergence']})")
        lines.append("")
    div_alerts: List[str] = results.get("divergence_alerts", [])
    for a in div_alerts:
        lines.append(f"> **Hallazgo:** {a}")
        lines.append("")
    lines.append("---")
    lines.append("")

    # Conclusiones automáticas
    lines.append("## Conclusiones Automáticas")
    lines.append("")

    # Feature con mayor correlación bruta
    if not corr_df.empty and "focus_score_mean" in corr_df.columns:
        target_abs = corr_df["focus_score_mean"].drop(
            "focus_score_mean", errors="ignore"
        ).abs().dropna().sort_values(ascending=False)
        if not target_abs.empty:
            best_feat = target_abs.index[0]
            best_r = corr_df["focus_score_mean"].get(best_feat, 0)
            lines.append(
                f"- **Feature más influyente:** `{best_feat}` (ρ = {best_r:.3f})"
            )

    # Lag óptimo
    if not lag_df.empty:
        valid_lags = lag_df.dropna(subset=["spearman_r"])
        if not valid_lags.empty:
            best_lag_row = valid_lags.loc[valid_lags["spearman_r"].abs().idxmax()]
            lines.append(
                f"- **Mejor lag:** `{best_lag_row['feature']}` con lag "
                f"{int(best_lag_row['lag'])}d "
                f"(ρ = {best_lag_row['spearman_r']:.3f})"
            )

    # R² del modelo
    if reg_info:
        lines.append(
            f"- **Capacidad predictiva lineal:** R² = "
            f"{reg_info.get('r_squared', 0):.3f}"
        )

    lines.append("")

    # Escribir archivo
    report_path = output_dir / report_name
    report_path.write_text("\n".join(lines), encoding="utf-8")

    return report_path


# ============================================================
# 9. Orquestador principal
# ============================================================


def main(db_path: Optional[str] = None) -> None:
    """
    Ejecuta el pipeline completo de análisis de correlación semanal.

    1. Carga datos de las 3 tablas.
    2. Valida suficiencia.
    3. Ejecuta 5 bloques de análisis.
    4. Genera reporte Markdown con figuras.

    Args:
        db_path: Ruta opcional a metrics.db. Si None, usa la ruta por defecto.
    """
    _apply_style()

    # Resolver paths
    project_root = Path(__file__).resolve().parent.parent.parent
    output_dir = project_root / "docs" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    engine = get_engine(db_path)

    print("=" * 60)
    print("  Análisis de Correlación Semanal — Dialektos")
    print("=" * 60)

    # 1. Cargar datos
    print("\n[1/7] Cargando datos...")
    df = load_analysis_dataframe(engine)
    print(f"  → {len(df)} días cargados.")

    # 2. Validar suficiencia
    print("[2/7] Validando suficiencia de datos...")
    warnings = check_data_sufficiency(df)
    for w in warnings:
        print(f"  ⚠ {w}")

    if df.empty:
        print("\n✗ Sin datos. Abortando.")
        return

    figures: Dict[str, plt.Figure] = {}
    results: Dict[str, Any] = {}

    # 3. Matriz de correlación
    print("[3/7] Calculando matriz de correlación...")
    fig_corr, corr_df, corr_alerts = correlation_matrix(df)
    figures["correlation_matrix"] = fig_corr
    results["correlation_matrix"] = corr_df
    results["correlation_alerts"] = corr_alerts
    print(f"  → {len(corr_df)} features incluidas.")

    # 4. Lag analysis
    print("[4/7] Analizando lags temporales...")
    fig_lag, lag_df, lag_alerts = lag_analysis(df)
    figures["lag_analysis"] = fig_lag
    results["lag_analysis"] = lag_df
    results["lag_alerts"] = lag_alerts
    print(f"  → {len(lag_df)} combinaciones feature×lag evaluadas.")

    # 5. Correlación parcial
    print("[5/7] Calculando correlaciones parciales...")
    fig_partial, partial_df, partial_alerts = partial_correlation(df)
    figures["partial_correlation"] = fig_partial
    results["partial_correlation"] = partial_df
    results["partial_alerts"] = partial_alerts
    print(f"  → {len(partial_df)} features evaluadas.")

    # 6. Validación de pesos ICD
    print("[6/7] Validando pesos ICD con regresión OLS...")
    fig_icd, reg_info, icd_alerts = validate_icd_weights(df)
    figures["icd_weights"] = fig_icd
    results["icd_weights"] = reg_info
    results["icd_alerts"] = icd_alerts
    if reg_info:
        print(f"  → R² = {reg_info.get('r_squared', 0):.3f}")

    # 7. Divergencia objetivo-subjetivo
    print("[7/7] Analizando divergencia objetivo vs subjetivo...")
    fig_div, div_alerts = divergence_analysis(df)
    figures["divergence"] = fig_div
    results["divergence_alerts"] = div_alerts

    # Generar reporte
    print("\nGenerando reporte Markdown...")
    all_alerts = warnings + corr_alerts + lag_alerts + partial_alerts + icd_alerts + div_alerts
    report_path = generate_report(df, figures, results, all_alerts, output_dir)
    print(f"\n✓ Reporte guardado: {report_path}")
    print(f"  Figuras en: {output_dir / 'figures'}")
    print("=" * 60)


# ============================================================
# CLI entry point
# ============================================================


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Análisis de correlación semanal — Dialektos Bio-Adaptabilidad"
    )
    parser.add_argument(
        "--db", type=str, default=None,
        help="Ruta a metrics.db (por defecto: data/metrics.db)",
    )
    args = parser.parse_args()
    main(db_path=args.db)
