"""
Página: Visualización del ICD en Tiempo Real

Dashboard principal con diseño moderno inspirado en v0:
- Hero section con gauge circular grande del ICD
- Grid de métricas biométricas destacadas
- Plan sugerido según ICD (badge con color)
- Racha de estudio (heatmap de días)
- Gráfico de tendencia últimos 7/14 días
- Leyenda de zonas cognitivas

Referencia: docs/TAREAS.md § Módulo 4 — Visualización del ICD.

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import streamlit as st
from sqlmodel import Session, select

from src.bio.decision import get_all_strategies, get_strategy, get_strategy_for_record
from src.bio.models import StudySession
from src.ui.components import (
    COLORS,
    get_recent_biometrics,
    get_recent_sessions,
    get_today_biometrics,
    render_icd_breakdown,
    render_icd_gauge,
    render_study_plan_badge,
    render_study_streak_heatmap,
    render_trend_chart,
)


def render_icd_dashboard(engine: Any) -> None:
    """Renderiza la página completa del ICD Dashboard con diseño moderno."""

    st.markdown("# Panel de Control")
    st.caption("Tu cockpit cognitivo personalizado")

    with Session(engine) as session:
        today_record = get_today_biometrics(session)
        recent_records = get_recent_biometrics(session, days=14)
        recent_sessions = get_recent_sessions(session, limit=100)

    icd_score = today_record.icd_score if today_record else None
    strategy = get_strategy(icd_score) if icd_score is not None else None
    zone_color = strategy.color if strategy else COLORS["text_muted"]

    # ── Hero Section: ICD Gauge Grande ──
    st.markdown(
        f"""
        <div style="
            border: 2px solid {zone_color};
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            background: linear-gradient(135deg, {zone_color}08, {zone_color}02);
        ">
        """,
        unsafe_allow_html=True,
    )

    hero_col1, hero_col2 = st.columns([1.2, 1])

    with hero_col1:
        if icd_score is not None:
            # Gauge circular grande mejorado
            render_icd_gauge(icd_score, height=350)
        else:
            st.info("Sin datos de ICD para hoy. Completa el formulario de datos fisiológicos.")

    with hero_col2:
        st.markdown("### Índice Cognitivo Diario (ICD)")
        if strategy:
            st.markdown(
                f"""
                <div style="
                    display: inline-block;
                    background: {zone_color}22;
                    border: 1px solid {zone_color}44;
                    border-radius: 20px;
                    padding: 8px 16px;
                    margin-bottom: 16px;
                ">
                    <span style="color: {zone_color}; font-weight: 600; font-size: 1.1em;">
                        Zona: {strategy.name}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.caption("Sin datos disponibles")

        # Plan de estudio mejorado
        render_study_plan_badge(icd_score)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Grid de Métricas Biométricas ──
    st.markdown("### Métricas Biométricas")
    bio_col1, bio_col2, bio_col3, bio_col4 = st.columns(4)

    with bio_col1:
        if today_record and today_record.hrv_rmssd:
            ln_rmssd = today_record.ln_rmssd or 0
            trend_icon = "📈" if today_record.ln_rmssd and today_record.hrv_baseline_7d and today_record.ln_rmssd > today_record.hrv_baseline_7d else "📉"
            st.markdown(
                f"""
                <div style="
                    background: {COLORS['bg_card']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 16px;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 0.9em; color: {COLORS['text_muted']}; font-weight: 500;">VFC (lnRMSSD)</span>
                        <span style="font-size: 1.2em;">❤️</span>
                    </div>
                    <div style="font-size: 1.8em; font-weight: 700; color: {COLORS['text']};">
                        {today_record.hrv_rmssd:.0f} ms
                    </div>
                    <div style="font-size: 0.85em; color: {COLORS['text_muted']}; margin-top: 4px;">
                        ln: {ln_rmssd:.2f} {trend_icon}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.metric("VFC (lnRMSSD)", "—", help="Variabilidad de frecuencia cardíaca")

    with bio_col2:
        if today_record and today_record.sleep_quality is not None:
            sleep_pct = today_record.sleep_quality
            st.markdown(
                f"""
                <div style="
                    background: {COLORS['bg_card']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 16px;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 0.9em; color: {COLORS['text_muted']}; font-weight: 500;">Calidad de Sueño</span>
                        <span style="font-size: 1.2em;">🌙</span>
                    </div>
                    <div style="font-size: 1.8em; font-weight: 700; color: {COLORS['text']}; margin-bottom: 8px;">
                        {sleep_pct}%
                    </div>
                    <div style="
                        background: {COLORS['border']};
                        border-radius: 4px;
                        height: 6px;
                        overflow: hidden;
                    ">
                        <div style="
                            background: {COLORS['normal']};
                            height: 100%;
                            width: {sleep_pct}%;
                            transition: width 0.3s;
                        "></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.metric("Calidad de Sueño", "—", help="Score de calidad de sueño")

    with bio_col3:
        if today_record and today_record.body_resources is not None:
            battery = today_record.body_resources
            st.markdown(
                f"""
                <div style="
                    background: {COLORS['bg_card']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 16px;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 0.9em; color: {COLORS['text_muted']}; font-weight: 500;">Batería Corporal</span>
                        <span style="font-size: 1.2em;">🔋</span>
                    </div>
                    <div style="font-size: 1.8em; font-weight: 700; color: {COLORS['text']}; margin-bottom: 8px;">
                        {battery}/100
                    </div>
                    <div style="
                        background: {COLORS['border']};
                        border-radius: 4px;
                        height: 6px;
                        overflow: hidden;
                    ">
                        <div style="
                            background: {COLORS['peak']};
                            height: 100%;
                            width: {battery}%;
                            transition: width 0.3s;
                        "></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.metric("Batería Corporal", "—", help="Body Resources de Suunto")

    with bio_col4:
        recovery_text = "Óptima" if today_record and today_record.body_resources and today_record.body_resources > 70 else "Normal" if today_record and today_record.body_resources and today_record.body_resources > 50 else "Baja"
        st.markdown(
            f"""
            <div style="
                background: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 0.9em; color: {COLORS['text_muted']}; font-weight: 500;">Estado Recuperación</span>
                    <span style="font-size: 1.2em;">⚡</span>
                </div>
                <div style="font-size: 1.8em; font-weight: 700; color: {COLORS['text']};">
                    {recovery_text}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Racha de Estudio (Heatmap) ──
    st.markdown("### Racha de Estudio")
    st.caption("Últimos 28 días")
    with Session(engine) as session_for_heatmap:
        render_study_streak_heatmap(session_for_heatmap, recent_sessions, zone_color)

    st.divider()

    # ── Desglose de componentes ──
    st.markdown("### Desglose de Componentes")
    render_icd_breakdown(today_record)

    st.divider()

    # ── Tendencia últimos días ──
    st.markdown("### Tendencia ICD")
    days_option = st.radio(
        "Período",
        options=[7, 14],
        horizontal=True,
        format_func=lambda d: f"Últimos {d} días",
    )
    render_trend_chart(recent_records, days=days_option, height=320)

    st.divider()

    # ── Leyenda de zonas ──
    st.markdown("### Zonas Cognitivas")
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
