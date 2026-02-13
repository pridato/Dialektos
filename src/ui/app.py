"""
Punto de entrada Streamlit — Dialektos.

Uso:
    streamlit run src/ui/app.py

Estructura multi-página con sidebar de navegación y estado actual del ICD.

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al PYTHONPATH
# Esto permite que Python encuentre el módulo 'src' cuando Streamlit ejecuta este archivo
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from datetime import date as date_type
from typing import Optional

import streamlit as st
from sqlmodel import Session, select

from src.bio.db import get_engine
from src.bio.models import DailyBiometrics

# ---------------------------------------------------------------------------
# Configuración global de la página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Dialektos",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Motor de base de datos (singleton via cache de Streamlit)
# ---------------------------------------------------------------------------


@st.cache_resource
def _get_engine():
    """Devuelve el motor SQLAlchemy reutilizable entre reruns."""
    return get_engine()


# ---------------------------------------------------------------------------
# Helper: obtener ICD del día actual
# ---------------------------------------------------------------------------


def _get_today_icd() -> Optional[float]:
    """Consulta el ICD del día actual desde DailyBiometrics."""
    engine = _get_engine()
    with Session(engine) as session:
        record = session.exec(
            select(DailyBiometrics).where(
                DailyBiometrics.date == date_type.today()
            )
        ).first()
        if record is not None and record.icd_score is not None:
            return record.icd_score
    return None


# ---------------------------------------------------------------------------
# Sidebar: navegación + ICD del día
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 8px 0;">
            <h1 style="font-size: 1.8em; margin: 0; color: #c9d1d9;">Dialektos</h1>
            <p style="font-size: 0.85em; color: #8b949e; margin: 4px 0 0 0;">Sistema RAG Adaptativo</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # Mostrar ICD actual como métrica destacada mejorada
    icd_today = _get_today_icd()
    if icd_today is not None:
        from src.bio.decision import get_strategy
        
        strategy = get_strategy(icd_today)
        zone_color = strategy.color
        
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, {zone_color}22, {zone_color}08);
                border: 1px solid {zone_color}44;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 8px;
            ">
                <div style="font-size: 0.85em; color: #8b949e; margin-bottom: 4px;">ICD Hoy</div>
                <div style="font-size: 2.2em; font-weight: 700; color: {zone_color};">
                    {icd_today:.1f}
                </div>
                <div style="margin-top: 8px;">
                    <span style="
                        display: inline-block;
                        background: {zone_color}44;
                        color: {zone_color};
                        padding: 4px 12px;
                        border-radius: 12px;
                        font-size: 0.85em;
                        font-weight: 600;
                    ">
                        {strategy.emoji} {strategy.name}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="
                background: #1a1d23;
                border: 1px solid #30363d;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 8px;
            ">
                <div style="font-size: 0.85em; color: #8b949e; margin-bottom: 4px;">ICD Hoy</div>
                <div style="font-size: 2.2em; font-weight: 700; color: #8b949e;">—</div>
                <div style="margin-top: 8px; font-size: 0.8em; color: #8b949e;">
                    Sin datos biométricos
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # Navegación multi-página mejorada
    st.markdown(
        '<div style="font-size: 0.85em; color: #8b949e; margin-bottom: 8px; font-weight: 600;">NAVEGACIÓN</div>',
        unsafe_allow_html=True,
    )
    
    page = st.radio(
        "Navegación",
        options=[
            "Dashboard ICD",
            "Entrada de Datos",
            "Tracking Sesiones",
            "Correlaciones",
            "Chat",
        ],
        label_visibility="collapsed",
    )
    
    st.divider()
    
    # Footer del sidebar
    st.markdown(
        """
        <div style="
            position: fixed;
            bottom: 16px;
            left: 16px;
            font-size: 0.75em;
            color: #8b949e;
        ">
            <div>🧠 Bio-Adaptive Learning</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Enrutamiento de páginas
# ---------------------------------------------------------------------------

if page == "Dashboard ICD":
    from src.ui.pages.icd_dashboard import render_icd_dashboard

    render_icd_dashboard(engine=_get_engine())

elif page == "Entrada de Datos":
    from src.ui.pages.data_entry import render_data_entry

    render_data_entry(engine=_get_engine())

elif page == "Tracking Sesiones":
    from src.ui.pages.tracking_sessions import render

    render(engine=_get_engine())

elif page == "Correlaciones":
    from src.ui.pages.correlation_dashboard import render_correlation_dashboard

    render_correlation_dashboard(engine=_get_engine())

elif page == "Chat":
    from src.ui.pages.chat import render_chat

    render_chat(engine=_get_engine())
