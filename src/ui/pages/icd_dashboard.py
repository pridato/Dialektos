"""
Página: Visualización del ICD en Tiempo Real

Dashboard principal con:
- Gauge semicircular del ICD (0-100)
- Desglose de componentes (HRV 25%, Sueño 20%, Recursos 20%, etc.)
- Plan sugerido según ICD (badge con color)
- Gráfico de tendencia últimos 7/14 días
- Leyenda de zonas cognitivas

Referencia: docs/TAREAS.md § Módulo 4 — Visualización del ICD.

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

from typing import Any

import streamlit as st
from sqlmodel import Session

from src.bio.decision import get_all_strategies, get_strategy_for_record
from src.ui.components import (
    COLORS,
    get_recent_biometrics,
    get_today_biometrics,
    render_icd_breakdown,
    render_icd_gauge,
    render_study_plan_badge,
    render_trend_chart,
)


def render_icd_dashboard(engine: Any) -> None:
    """Renderiza la página completa del ICD Dashboard."""

    st.markdown("# Índice Cognitivo Diario (ICD)")
    st.caption(
        "Tu estado cognitivo actual basado en métricas biológicas y subjetivas. "
        "El ICD determina qué y cómo estudiar hoy."
    )

    with Session(engine) as session:
        today_record = get_today_biometrics(session)
        recent_records = get_recent_biometrics(session, days=14)

    icd_score = today_record.icd_score if today_record else None

    # ── Sección superior: Gauge + Plan sugerido ──
    col_gauge, col_plan = st.columns([1, 1])

    with col_gauge:
        st.subheader("Estado Actual")
        render_icd_gauge(icd_score, height=300)

    with col_plan:
        st.subheader("Plan de Estudio")
        render_study_plan_badge(icd_score)

        # Métricas derivadas rápidas
        if today_record:
            st.markdown("---")
            mcol1, mcol2, mcol3 = st.columns(3)
            with mcol1:
                val = f"{today_record.ln_rmssd:.2f}" if today_record.ln_rmssd else "—"
                st.metric("ln(RMSSD)", val, help="Logaritmo natural del HRV")
            with mcol2:
                val = f"{today_record.hrv_baseline_7d:.2f}" if today_record.hrv_baseline_7d else "—"
                st.metric("Baseline 7d", val, help="EMA 7 días de ln_rmssd")
            with mcol3:
                val = f"{today_record.sleep_consistency:.1f} min" if today_record.sleep_consistency else "—"
                st.metric("Consistencia Sueño", val, help="Std dev hora de dormir (7d)")

    st.divider()

    # ── Desglose de componentes ──
    st.subheader("Desglose de Componentes")
    render_icd_breakdown(today_record)

    st.divider()

    # ── Tendencia últimos días ──
    st.subheader("Tendencia ICD")
    days_option = st.radio(
        "Período",
        options=[7, 14],
        horizontal=True,
        format_func=lambda d: f"Últimos {d} días",
    )
    render_trend_chart(recent_records, days=days_option, height=320)

    st.divider()

    # ── Leyenda de zonas ──
    st.subheader("Zonas Cognitivas")
    strategies = get_all_strategies()

    cols = st.columns(4)
    for col, strat in zip(cols, strategies):
        with col:
            st.markdown(
                f"""
                <div style="
                    background: {strat.color}11;
                    border: 1px solid {strat.color}33;
                    border-radius: 8px;
                    padding: 12px;
                    text-align: center;
                    min-height: 130px;
                ">
                    <div style="font-size: 1.8em;">{strat.emoji}</div>
                    <div style="font-weight: 700; color: {strat.color}; font-size: 1.05em;">
                        {strat.name}
                    </div>
                    <div style="color: {COLORS['text_muted']}; font-size: 0.8em; margin-top: 4px;">
                        {strat.zone.value.upper()}
                    </div>
                    <div style="color: {COLORS['text_muted']}; font-size: 0.75em; margin-top: 4px;">
                        Modo IA: {strat.ai_mode.value.capitalize()}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
