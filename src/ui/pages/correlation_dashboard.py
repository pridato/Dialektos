"""
Página: Dashboard de Correlación HRV-Rendimiento

Visualización interactiva de los análisis del módulo 3.7:
- Scatter plots: HRV vs Focus, HRV vs Comprensión, HRV vs Retención
- Coeficiente de Pearson + línea de regresión
- Alerta si datos < 30 días o correlación < 0.3
- Tabla de estadísticas descriptivas
- Integración con analysis.py para reportes completos

Referencia: docs/TAREAS.md § Módulo 4 — Dashboard de Correlación.

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
import streamlit as st
from sqlmodel import Session

from src.bio.analysis import (
    ANALYSIS_FEATURES,
    check_data_sufficiency,
    correlation_matrix,
    divergence_analysis,
    lag_analysis,
    load_analysis_dataframe,
    partial_correlation,
    validate_icd_weights,
)
from src.ui.components import COLORS, render_correlation_chart


def render_correlation_dashboard(engine: Any) -> None:
    """Renderiza la página del Dashboard de Correlación HRV-Rendimiento."""

    st.markdown("# Dashboard de Correlación HRV-Rendimiento")
    st.caption(
        "Análisis estadístico de la relación entre tus métricas biológicas "
        "y tu rendimiento de estudio. Requiere datos suficientes."
    )

    # ── Cargar datos ──
    df = load_analysis_dataframe(engine)

    if df.empty:
        st.warning(
            "No hay datos en la base de datos. "
            "Registra tus datos fisiológicos y sesiones de estudio primero."
        )
        return

    # ── Validación de suficiencia ──
    warnings = check_data_sufficiency(df)

    if warnings:
        with st.expander("Advertencias sobre los datos", expanded=True):
            for w in warnings:
                st.warning(w)

    # ── Estadísticas descriptivas ──
    st.subheader("Resumen de Datos")

    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    with stat_col1:
        st.metric("Días registrados", len(df))
    with stat_col2:
        sessions_count = int(df["n_sessions"].sum()) if "n_sessions" in df.columns else 0
        st.metric("Sesiones totales", sessions_count)
    with stat_col3:
        date_range = f"{df['date'].min()} → {df['date'].max()}" if not df.empty else "—"
        st.metric("Rango", date_range)
    with stat_col4:
        avg_icd = df["icd_score"].mean() if "icd_score" in df.columns else None
        st.metric("ICD Promedio", f"{avg_icd:.1f}" if avg_icd and not np.isnan(avg_icd) else "—")

    # Tabla descriptiva
    desc_cols = [c for c in ANALYSIS_FEATURES + ["focus_score_mean"] if c in df.columns]
    if desc_cols:
        with st.expander("Estadísticas Descriptivas"):
            desc_df = df[desc_cols].describe().round(2)
            st.dataframe(desc_df, use_container_width=True)

    st.divider()

    # ============================================================
    # TABS DE ANÁLISIS
    # ============================================================

    tab_scatter, tab_corr, tab_lag, tab_partial, tab_weights, tab_divergence = st.tabs([
        "Scatter Plots",
        "Matriz Correlación",
        "Análisis Lag",
        "Correlación Parcial",
        "Validación Pesos ICD",
        "Divergencia Obj-Subj",
    ])

    # ── Tab 1: Scatter Plots Interactivos ──
    with tab_scatter:
        st.subheader("Correlaciones Bivariadas")
        st.caption("Selecciona las variables para explorar sus relaciones.")

        available_cols = [c for c in df.columns if df[c].dtype in ["float64", "int64", "Float64", "Int64"]]
        available_cols = [c for c in available_cols if df[c].notna().sum() >= 3]

        sc_col1, sc_col2 = st.columns(2)
        with sc_col1:
            x_var = st.selectbox(
                "Variable X",
                options=available_cols,
                index=available_cols.index("icd_score") if "icd_score" in available_cols else 0,
            )
        with sc_col2:
            default_y = "focus_score_mean" if "focus_score_mean" in available_cols else available_cols[0]
            y_var = st.selectbox(
                "Variable Y",
                options=available_cols,
                index=available_cols.index(default_y) if default_y in available_cols else 0,
            )

        if x_var and y_var:
            render_correlation_chart(
                df, x_var, y_var,
                title=f"{x_var} vs {y_var}",
                height=450,
            )

        # Scatter plots predefinidos
        st.markdown("---")
        st.markdown("**Correlaciones Clave (predefinidas)**")

        predefined_pairs = [
            ("icd_score", "focus_score_mean", "ICD vs Focus Score"),
            ("body_resources", "focus_score_mean", "Body Resources vs Focus"),
            ("ln_rmssd", "focus_score_mean", "ln(RMSSD) vs Focus"),
            ("sleep_quality", "focus_score_mean", "Calidad Sueño vs Focus"),
            ("energy_level", "focus_score_mean", "Energía vs Focus"),
        ]

        valid_pairs = [
            (x, y, t) for x, y, t in predefined_pairs
            if x in df.columns and y in df.columns
            and df[[x, y]].dropna().shape[0] >= 3
        ]

        if valid_pairs:
            pair_cols = st.columns(min(len(valid_pairs), 2))
            for idx, (x, y, title) in enumerate(valid_pairs):
                with pair_cols[idx % 2]:
                    render_correlation_chart(df, x, y, title=title, height=350)
        else:
            st.info(
                "Necesitas registrar sesiones de estudio (con focus_score) "
                "para ver correlaciones con rendimiento."
            )

    # ── Tab 2: Matriz de Correlación ──
    with tab_corr:
        st.subheader("Matriz de Correlación (Spearman)")
        st.caption(
            "Correlaciones no paramétricas entre todas las features. "
            "Spearman es robusto con muestras pequeñas."
        )

        fig_corr, corr_df, corr_alerts = correlation_matrix(df)

        st.pyplot(fig_corr, use_container_width=True)

        if corr_alerts:
            for alert in corr_alerts:
                st.warning(alert)

        if not corr_df.empty and "focus_score_mean" in corr_df.columns:
            st.markdown("**Correlaciones con focus_score_mean:**")
            target_corrs = (
                corr_df["focus_score_mean"]
                .drop("focus_score_mean", errors="ignore")
                .sort_values(ascending=False)
            )
            corr_display = pd.DataFrame({
                "Feature": target_corrs.index,
                "Spearman ρ": target_corrs.values,
                "|ρ|": target_corrs.abs().values,
            })
            st.dataframe(corr_display.round(3), use_container_width=True, hide_index=True)

    # ── Tab 3: Análisis de Lag ──
    with tab_lag:
        st.subheader("Detección de Lag Temporal")
        st.caption(
            "¿El sueño de anteayer afecta más al estudio de hoy que el de ayer? "
            "Analiza retardos de 0 a 3 días."
        )

        fig_lag, lag_df, lag_alerts = lag_analysis(df)

        st.pyplot(fig_lag, use_container_width=True)

        if lag_alerts:
            st.markdown("**Hallazgos:**")
            for alert in lag_alerts:
                st.info(alert)

        if not lag_df.empty:
            with st.expander("Tabla de coeficientes por feature y lag"):
                pivot = lag_df.pivot_table(
                    index="feature", columns="lag",
                    values="spearman_r", aggfunc="first",
                )
                pivot.columns = [f"Lag {int(c)}d" for c in pivot.columns]
                st.dataframe(pivot.round(3), use_container_width=True)

    # ── Tab 4: Correlación Parcial ──
    with tab_partial:
        st.subheader("Correlación Parcial (controlando confounders)")
        st.caption(
            "Aísla el efecto real de cada feature eliminando la influencia "
            "de cafeína y ejercicio."
        )

        fig_partial, partial_df, partial_alerts = partial_correlation(df)

        st.pyplot(fig_partial, use_container_width=True)

        if partial_alerts:
            st.markdown("**Hallazgos:**")
            for alert in partial_alerts:
                st.info(alert)

        if not partial_df.empty:
            with st.expander("Tabla comparativa"):
                display_df = partial_df[["feature", "r_raw", "r_partial", "delta"]].copy()
                display_df.columns = ["Feature", "r Bruta", "r Parcial", "Δ"]
                st.dataframe(display_df.round(3), use_container_width=True, hide_index=True)

    # ── Tab 5: Validación Pesos ICD ──
    with tab_weights:
        st.subheader("Validación de Pesos ICD (Regresión OLS)")
        st.caption(
            "Compara los pesos manuales de la fórmula ICD con los pesos "
            "aprendidos por regresión lineal múltiple."
        )

        fig_weights, reg_info, icd_alerts = validate_icd_weights(df)

        st.pyplot(fig_weights, use_container_width=True)

        if reg_info:
            r_sq = reg_info.get("r_squared", 0)
            n_obs = reg_info.get("n_observations", 0)
            st.metric(
                "R² del modelo",
                f"{r_sq:.3f}",
                help=f"Varianza explicada por el modelo lineal (n={n_obs}).",
            )

            if "features" in reg_info:
                st.markdown("**Comparación de pesos:**")
                weight_rows = []
                for feat, info in reg_info["features"].items():
                    diff = abs(info["learned_weight"] - info["manual_weight"])
                    weight_rows.append({
                        "Feature": feat,
                        "Peso Manual": info["manual_weight"],
                        "Peso Aprendido": info["learned_weight"],
                        "Δ": diff,
                        "Alerta": "Si" if diff > 0.15 else "",
                    })
                st.dataframe(
                    pd.DataFrame(weight_rows).round(3),
                    use_container_width=True,
                    hide_index=True,
                )

        if icd_alerts:
            for alert in icd_alerts:
                st.warning(alert)

    # ── Tab 6: Divergencia Objetivo-Subjetivo ──
    with tab_divergence:
        st.subheader("Divergencia Objetivo vs Subjetivo")
        st.caption(
            "Scatter de body_resources (objetivo) vs energy_level (subjetivo). "
            "Detecta días donde biología y percepción divergen."
        )

        fig_div, div_alerts = divergence_analysis(df)

        st.pyplot(fig_div, use_container_width=True)

        if div_alerts:
            st.markdown("**Hallazgos:**")
            for alert in div_alerts:
                st.info(alert)

        st.markdown(
            f"""
            <div style="
                background: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 14px;
                margin-top: 12px;
                font-size: 0.9em;
                color: {COLORS['text_muted']};
            ">
                <b>Interpretación:</b> Puntos sobre la diagonal indican que tu percepción
                de energía es mayor que lo que indican tus recursos corporales (optimismo fisiológico).
                Puntos bajo la diagonal indican que te sientes peor de lo que tu cuerpo muestra
                (posible factor psicológico). Los outliers (>25 puntos de divergencia) se marcan en rojo.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Generar reporte completo ──
    st.subheader("Generar Reporte Completo")
    st.caption(
        "Ejecuta el pipeline completo de analysis.py y genera un reporte "
        "Markdown con todas las figuras en docs/reports/."
    )

    if st.button("Generar Reporte Semanal", type="primary"):
        with st.spinner("Generando reporte..."):
            try:
                from src.bio.analysis import main as run_analysis
                run_analysis()
                st.success(
                    "Reporte generado en `docs/reports/`. "
                    "Consulta el archivo Markdown y las figuras PNG."
                )
            except Exception as e:
                st.error(f"Error al generar reporte: {e}")
