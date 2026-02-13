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
    st.title("Dialektos")
    st.caption("Bio-Adaptive Learning System")

    st.divider()

    # Mostrar ICD actual como métrica destacada
    icd_today = _get_today_icd()
    if icd_today is not None:
        st.metric(label="ICD Hoy", value=f"{icd_today:.1f}")
        # Color semántico según zona cognitiva
        if icd_today > 80:
            st.success("Peak — Deep Work")
        elif icd_today > 50:
            st.info("Normal — Flow")
        elif icd_today > 30:
            st.warning("Fatigue — Review")
        else:
            st.error("Burnout — Survival")
    else:
        st.metric(label="ICD Hoy", value="—")
        st.caption("Sin datos biométricos para hoy.")

    st.divider()

    # Navegación multi-página
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
