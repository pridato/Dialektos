"""
Componentes UI Reutilizables — Módulo 4 Dialektos

Funciones helper para renderizar elementos visuales consistentes
a lo largo de toda la interfaz Streamlit:

- render_icd_gauge(): Gauge circular del ICD con color según zona.
- render_icd_breakdown(): Desglose de componentes del ICD.
- render_study_plan_badge(): Badge con estrategia pedagógica.
- render_trend_chart(): Gráfico de tendencia ICD últimos N días.
- render_correlation_chart(): Scatter con línea de regresión.
- render_session_table(): Tabla estilizada de sesiones de estudio.

Los colores siguen el esquema definido en src/bio/decision.py:
    - Verde (#22c55e): PEAK
    - Azul (#3b82f6): NORMAL
    - Amarillo (#f59e0b): FATIGUE
    - Rojo (#ef4444): BURNOUT

Referencia: docs/TAREAS.md § Módulo 4 — Componentes UI Reutilizables.

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

from datetime import date as date_type
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlmodel import Session, select

from src.bio.decision import (
    CognitiveZone,
    PedagogicalStrategy,
    get_all_strategies,
    get_strategy,
    get_threshold_ranges,
)
from src.bio.models import DailyBiometrics, StudySession


# ============================================================================
# PALETA DE COLORES GLOBAL
# ============================================================================

COLORS: Dict[str, str] = {
    "peak": "#22c55e",
    "normal": "#3b82f6",
    "fatigue": "#f59e0b",
    "burnout": "#ef4444",
    "bg_dark": "#0e1117",
    "bg_card": "#1a1d23",
    "text": "#c9d1d9",
    "text_muted": "#8b949e",
    "border": "#30363d",
    "accent": "#58a6ff",
}

ZONE_COLORS: Dict[CognitiveZone, str] = {
    CognitiveZone.PEAK: COLORS["peak"],
    CognitiveZone.NORMAL: COLORS["normal"],
    CognitiveZone.FATIGUE: COLORS["fatigue"],
    CognitiveZone.BURNOUT: COLORS["burnout"],
}


# ============================================================================
# 1. ICD GAUGE (Indicador circular)
# ============================================================================


def render_icd_gauge(icd_score: Optional[float], height: int = 280) -> None:
    """
    Renderiza un gauge semicircular del ICD (0-100) con color según zona cognitiva.

    El gauge muestra:
    - Arco coloreado según la zona (PEAK/NORMAL/FATIGUE/BURNOUT)
    - Valor numérico central grande
    - Nombre de la zona debajo

    Args:
        icd_score: Valor del ICD (0-100). Si None, muestra "Sin datos".
        height: Altura del gráfico en píxeles.
    """
    if icd_score is None:
        st.info("Sin datos de ICD para hoy. Completa el formulario de datos fisiológicos.")
        return

    strategy: PedagogicalStrategy = get_strategy(icd_score)
    color: str = strategy.color

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=icd_score,
        number={"font": {"size": 48, "color": color}, "suffix": ""},
        title={
            "text": f"{strategy.emoji} {strategy.name}",
            "font": {"size": 18, "color": COLORS["text"]},
        },
        gauge={
            "axis": {
                "range": [0, 100],
                "tickwidth": 1,
                "tickcolor": COLORS["border"],
                "tickfont": {"color": COLORS["text_muted"], "size": 10},
            },
            "bar": {"color": color, "thickness": 0.75},
            "bgcolor": COLORS["bg_card"],
            "borderwidth": 0,
            "steps": [
                {"range": [0, 30], "color": "rgba(239,68,68,0.15)"},
                {"range": [30, 50], "color": "rgba(245,158,11,0.15)"},
                {"range": [50, 80], "color": "rgba(59,130,246,0.15)"},
                {"range": [80, 100], "color": "rgba(34,197,94,0.15)"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 2},
                "thickness": 0.8,
                "value": icd_score,
            },
        },
    ))

    fig.update_layout(
        height=height,
        margin=dict(l=30, r=30, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": COLORS["text"]},
    )

    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# 2. DESGLOSE DE COMPONENTES ICD
# ============================================================================


def render_icd_breakdown(record: Optional[DailyBiometrics]) -> None:
    """
    Muestra el desglose de componentes que alimentan el ICD.

    Presenta métricas KPI con st.metric(): HRV, Sueño, Recursos,
    Energía, Claridad Mental y Mood, cada uno con su peso en la fórmula.

    Args:
        record: Registro DailyBiometrics del día. Si None, muestra placeholder.
    """
    if record is None:
        st.caption("Completa los datos del día para ver el desglose.")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="HRV (RMSSD)",
            value=f"{record.hrv_rmssd:.0f} ms" if record.hrv_rmssd else "—",
            help="Peso en ICD: 25%. Actividad parasimpática nocturna.",
        )
        st.metric(
            label="Calidad Sueño",
            value=f"{record.sleep_quality}%" if record.sleep_quality is not None else "—",
            help="Peso en ICD: 20%. Score de Suunto (0-100).",
        )

    with col2:
        st.metric(
            label="Body Resources",
            value=f"{record.body_resources}" if record.body_resources is not None else "—",
            help="Peso en ICD: 20%. Índice integrado de recuperación Suunto.",
        )
        st.metric(
            label="Energía",
            value=f"{record.energy_level}/10" if record.energy_level is not None else "—",
            help="Peso en ICD: 15%. Sensación subjetiva de energía física.",
        )

    with col3:
        st.metric(
            label="Claridad Mental",
            value=f"{record.mental_clarity}/10" if record.mental_clarity is not None else "—",
            help="Peso en ICD: 10%. Agudeza cognitiva subjetiva.",
        )
        mood_display = record.mood.capitalize() if record.mood else "—"
        st.metric(
            label="Estado de Ánimo",
            value=mood_display,
            help="Peso en ICD: 10%. Focused (+1.0), Neutral (0), Anxious (-0.3), Tired (-0.5).",
        )


# ============================================================================
# 3. BADGE DE ESTRATEGIA PEDAGÓGICA
# ============================================================================


def render_study_plan_badge(icd_score: Optional[float]) -> None:
    """
    Renderiza un badge visual con la estrategia pedagógica sugerida.

    Muestra nombre, emoji, modo IA, descripción y tareas recomendadas
    con el color correspondiente a la zona cognitiva.

    Args:
        icd_score: Valor del ICD. Si None, muestra placeholder.
    """
    if icd_score is None:
        st.info("Registra tus datos fisiológicos para obtener un plan de estudio adaptado.")
        return

    strategy: PedagogicalStrategy = get_strategy(icd_score)
    color: str = strategy.color

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {color}22, {color}08);
            border: 1px solid {color}44;
            border-left: 4px solid {color};
            border-radius: 8px;
            padding: 16px 20px;
            margin: 8px 0;
        ">
            <div style="font-size: 1.4em; font-weight: 700; color: {color};">
                {strategy.emoji} {strategy.name}
            </div>
            <div style="color: {COLORS['text']}; margin-top: 6px; font-size: 0.95em;">
                {strategy.description}
            </div>
            <div style="margin-top: 10px; color: {COLORS['text_muted']}; font-size: 0.85em;">
                <b>Modo IA:</b> {strategy.ai_mode.value.capitalize()} &nbsp;|&nbsp;
                <b>Dificultad max:</b> {strategy.max_difficulty.value}
            </div>
            <div style="margin-top: 6px; color: {COLORS['text_muted']}; font-size: 0.85em;">
                <b>Tareas recomendadas:</b>
                {', '.join(t.value.replace('_', ' ').title() for t in strategy.recommended_tasks)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================================
# 4. GRÁFICO DE TENDENCIA ICD
# ============================================================================


def render_trend_chart(
    records: List[DailyBiometrics],
    days: int = 7,
    height: int = 300,
) -> None:
    """
    Renderiza un gráfico de línea con la tendencia del ICD.

    Muestra los últimos N días con zonas coloreadas de fondo
    y la línea del ICD con marcadores.

    Args:
        records: Lista de DailyBiometrics ordenados por fecha.
        days: Número de días a mostrar (default: 7).
        height: Altura del gráfico.
    """
    if not records:
        st.caption("Sin datos históricos para mostrar tendencia.")
        return

    # Filtrar últimos N días con ICD válido
    valid = [r for r in records if r.icd_score is not None]
    valid = sorted(valid, key=lambda r: r.date)[-days:]

    if not valid:
        st.caption("No hay valores de ICD calculados todavía.")
        return

    dates = [r.date.isoformat() for r in valid]
    scores = [r.icd_score for r in valid]

    # Colores por punto según zona
    point_colors = []
    for s in scores:
        if s is not None:
            strategy = get_strategy(s)
            point_colors.append(strategy.color)
        else:
            point_colors.append(COLORS["text_muted"])

    fig = go.Figure()

    # Bandas de zona
    zones = [
        ("Burnout", 0, 30, COLORS["burnout"]),
        ("Fatigue", 30, 50, COLORS["fatigue"]),
        ("Normal", 50, 80, COLORS["normal"]),
        ("Peak", 80, 100, COLORS["peak"]),
    ]
    for name, y0, y1, color in zones:
        fig.add_hrect(
            y0=y0, y1=y1,
            fillcolor=color, opacity=0.06,
            line_width=0,
            annotation_text=name,
            annotation_position="right",
            annotation_font_size=9,
            annotation_font_color=color,
        )

    # Línea de ICD
    fig.add_trace(go.Scatter(
        x=dates,
        y=scores,
        mode="lines+markers",
        line=dict(color=COLORS["accent"], width=2.5),
        marker=dict(
            color=point_colors,
            size=10,
            line=dict(width=1.5, color="white"),
        ),
        name="ICD",
        hovertemplate="<b>%{x}</b><br>ICD: %{y:.1f}<extra></extra>",
    ))

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=60, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=False,
            color=COLORS["text_muted"],
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            range=[0, 105],
            showgrid=True,
            gridcolor=COLORS["border"],
            gridwidth=0.5,
            color=COLORS["text_muted"],
            tickfont=dict(size=10),
        ),
        showlegend=False,
        font=dict(color=COLORS["text"]),
    )

    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# 5. GRÁFICO DE CORRELACIÓN (Scatter + Regresión)
# ============================================================================


def render_correlation_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "",
    height: int = 400,
) -> None:
    """
    Renderiza un scatter plot con línea de regresión y coeficiente de Pearson.

    Incluye:
    - Puntos coloreados
    - Línea de tendencia (OLS)
    - Anotación con r y p-value

    Args:
        df: DataFrame con los datos.
        x_col: Nombre de la columna para el eje X.
        y_col: Nombre de la columna para el eje Y.
        title: Título del gráfico.
        height: Altura del gráfico.
    """
    from scipy import stats as sp_stats

    sub = df[[x_col, y_col]].dropna()

    if len(sub) < 3:
        st.caption(f"Datos insuficientes para correlación {x_col} vs {y_col}.")
        return

    x_vals = sub[x_col].values
    y_vals = sub[y_col].values

    # Regresión lineal
    slope, intercept, r_value, p_value, std_err = sp_stats.linregress(x_vals, y_vals)
    x_line = np.linspace(x_vals.min(), x_vals.max(), 100)
    y_line = slope * x_line + intercept

    fig = go.Figure()

    # Puntos
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=y_vals,
        mode="markers",
        marker=dict(
            color=COLORS["accent"],
            size=8,
            opacity=0.7,
            line=dict(width=1, color="white"),
        ),
        name="Datos",
        hovertemplate=f"<b>{x_col}:</b> %{{x:.1f}}<br><b>{y_col}:</b> %{{y:.1f}}<extra></extra>",
    ))

    # Línea de regresión
    fig.add_trace(go.Scatter(
        x=x_line,
        y=y_line,
        mode="lines",
        line=dict(color=COLORS["peak"], width=2, dash="dash"),
        name=f"r = {r_value:.3f}",
    ))

    # Anotación
    sig = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
    fig.add_annotation(
        text=f"r = {r_value:.3f} ({sig}), p = {p_value:.4f}",
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        showarrow=False,
        font=dict(size=12, color=COLORS["text"]),
        bgcolor=COLORS["bg_card"],
        bordercolor=COLORS["border"],
        borderwidth=1,
        borderpad=6,
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=COLORS["text"])),
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title=x_col,
            showgrid=True,
            gridcolor=COLORS["border"],
            color=COLORS["text_muted"],
        ),
        yaxis=dict(
            title=y_col,
            showgrid=True,
            gridcolor=COLORS["border"],
            color=COLORS["text_muted"],
        ),
        font=dict(color=COLORS["text"]),
        showlegend=True,
        legend=dict(
            x=0.98, y=0.02, xanchor="right", yanchor="bottom",
            bgcolor="rgba(0,0,0,0.5)",
            font=dict(size=10),
        ),
    )

    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# 6. TABLA DE SESIONES DE ESTUDIO
# ============================================================================


def render_session_table(sessions: List[StudySession]) -> None:
    """
    Renderiza una tabla estilizada de sesiones de estudio.

    Muestra: fecha, hora, duración, tipo, dificultad, focus, flow.

    Args:
        sessions: Lista de StudySession ordenadas (más recientes primero).
    """
    if not sessions:
        st.caption("No hay sesiones de estudio registradas.")
        return

    rows: List[Dict[str, Any]] = []
    for s in sessions:
        rows.append({
            "Fecha": s.date.isoformat(),
            "Inicio": s.start_time.strftime("%H:%M") if s.start_time else "—",
            "Duración": f"{s.duration_min} min" if s.duration_min else "—",
            "Tipo": (s.task_type or "—").replace("_", " ").title(),
            "Dificultad": s.difficulty_attempted or "—",
            "Focus": f"{s.focus_score}/10" if s.focus_score else "—",
            "Comprensión": f"{s.comprehension_rate}%" if s.comprehension_rate is not None else "—",
            "Flow": "Si" if s.flow_state else ("No" if s.flow_state is False else "—"),
            "ICD": f"{s.icd_at_start:.0f}" if s.icd_at_start is not None else "—",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================================
# 7. HELPERS DE DATOS
# ============================================================================


def get_today_biometrics(session: Session) -> Optional[DailyBiometrics]:
    """Obtiene el registro biométrico del día actual."""
    from datetime import date
    today = date.today()
    stmt = select(DailyBiometrics).where(DailyBiometrics.date == today)
    return session.exec(stmt).first()


def get_recent_biometrics(
    session: Session,
    days: int = 14,
) -> List[DailyBiometrics]:
    """Obtiene los registros biométricos de los últimos N días."""
    from datetime import date, timedelta
    cutoff = date.today() - timedelta(days=days)
    stmt = (
        select(DailyBiometrics)
        .where(DailyBiometrics.date >= cutoff)
        .order_by(DailyBiometrics.date.asc())
    )
    return list(session.exec(stmt).all())


def get_recent_sessions(
    session: Session,
    limit: int = 20,
) -> List[StudySession]:
    """Obtiene las sesiones de estudio más recientes."""
    stmt = (
        select(StudySession)
        .order_by(StudySession.date.desc(), StudySession.start_time.desc())
        .limit(limit)
    )
    return list(session.exec(stmt).all())


def get_today_icd(session: Session) -> Optional[float]:
    """Obtiene el ICD score del día actual (shortcut)."""
    record = get_today_biometrics(session)
    if record and record.icd_score is not None:
        return record.icd_score
    return None


# ============================================================================
# 8. HEATMAP DE RACHA DE ESTUDIO
# ============================================================================


def render_study_streak_heatmap(
    session: Session,
    sessions: List[StudySession],
    zone_color: str,
) -> None:
    """
    Renderiza un heatmap tipo GitHub de los últimos 28 días mostrando días con sesiones de estudio.

    Args:
        session: Sesión de base de datos.
        sessions: Lista de sesiones de estudio.
        zone_color: Color de la zona actual para los días con estudio.
    """
    from datetime import date, timedelta

    # Crear diccionario de días con sesiones
    days_with_sessions = set()
    for s in sessions:
        days_with_sessions.add(s.date)

    # Generar últimos 28 días
    today = date.today()
    last_28_days = [today - timedelta(days=i) for i in range(27, -1, -1)]

    # Crear grid de 7x4 (semanas x días)
    weeks = []
    current_week = []
    for day in last_28_days:
        current_week.append(day)
        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []
    if current_week:
        weeks.append(current_week)

    # Renderizar heatmap
    html = f"""
    <div style="
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 16px;
        margin-top: 8px;
    ">
        <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; max-width: 600px;">
    """

    for week in weeks:
        for day in week:
            has_study = day in days_with_sessions
            opacity = "1.0" if has_study else "0.3"
            bg_color = zone_color if has_study else COLORS["border"]
            html += f"""
            <div
                style="
                    aspect-ratio: 1;
                    background-color: {bg_color};
                    opacity: {opacity};
                    border-radius: 4px;
                    cursor: pointer;
                    transition: opacity 0.2s;
                "
                title="{day.strftime('%Y-%m-%d')}"
            ></div>
            """

    html += f"""
        </div>
        <div style="margin-top: 12px; font-size: 0.85em; color: {COLORS['text_muted']};">
            <span style="display: inline-block; width: 12px; height: 12px; background: {zone_color}; border-radius: 2px; margin-right: 4px;"></span>
            Días con sesiones de estudio
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)
