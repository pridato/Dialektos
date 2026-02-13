"""
Página: Tracking de Sesiones de Estudio

Formulario al finalizar cada sesión + tabla histórica:
- Registro post-sesión: duración, tipo, dificultad, focus, comprensión, flow
- Enlace automático al ICD del día (icd_at_start)
- Tabla de sesiones anteriores con filtros
- Retención 24h opcional (para sesiones del día anterior)

Referencia: docs/TAREAS.md § Módulo 4 — Tracking de Sesiones + § 3.6.1.

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List

import streamlit as st
from sqlmodel import Session, select

from src.bio.models import (
    DailyBiometrics,
    DifficultyEnum,
    StudySession,
    TaskTypeEnum,
)
from src.ui.components import (
    COLORS,
    get_recent_sessions,
    get_today_biometrics,
    render_session_table,
)


def render_session_tracking(engine: Any) -> None:
    """Renderiza la página de Tracking de Sesiones de Estudio."""

    st.markdown("# Tracking de Sesiones de Estudio")
    st.caption(
        "Registra cada sesión de estudio al terminar. Los datos se enlazan "
        "automáticamente con tu ICD del día para validar correlaciones."
    )

    tab_new, tab_history, tab_retention = st.tabs([
        "Nueva Sesión",
        "Historial",
        "Retención 24h",
    ])

    # ============================================================
    # TAB 1: Nueva Sesión
    # ============================================================

    with tab_new:
        st.subheader("Registrar Sesión de Estudio")

        # Obtener ICD actual para snapshot
        with Session(engine) as session:
            today_record = get_today_biometrics(session)

        current_icd = today_record.icd_score if today_record else None

        if current_icd is not None:
            from src.bio.decision import get_strategy
            strat = get_strategy(current_icd)
            st.markdown(
                f"""
                <div style="
                    background: {strat.color}11;
                    border: 1px solid {strat.color}33;
                    border-radius: 8px;
                    padding: 10px 16px;
                    margin-bottom: 16px;
                ">
                    <span style="color: {strat.color}; font-weight: 700;">
                        {strat.emoji} ICD al inicio: {current_icd:.0f}
                    </span>
                    <span style="color: {COLORS['text_muted']}; margin-left: 12px;">
                        — {strat.name} ({strat.ai_mode.value.capitalize()})
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info(
                "No hay ICD calculado para hoy. Registra tus datos fisiológicos "
                "primero para enlazar automáticamente el ICD con la sesión."
            )

        with st.form("session_form", clear_on_submit=True):
            # ── Tiempo ──
            time_col1, time_col2, time_col3 = st.columns(3)

            with time_col1:
                session_date = st.date_input(
                    "Fecha de la sesión",
                    value=date.today(),
                    max_value=date.today(),
                )
            with time_col2:
                start_time = st.time_input(
                    "Hora de inicio",
                    value=datetime.now().replace(hour=max(0, datetime.now().hour - 1), minute=0),
                )
            with time_col3:
                duration_min = st.number_input(
                    "Duración (min)",
                    min_value=5,
                    max_value=480,
                    value=60,
                    step=5,
                    help="Tiempo real enfocado (sin contar descansos).",
                )

            st.divider()

            # ── Tipo y Dificultad ──
            type_col1, type_col2 = st.columns(2)

            with type_col1:
                task_type = st.selectbox(
                    "Tipo de Tarea",
                    options=[t.value for t in TaskTypeEnum],
                    format_func=lambda x: {
                        "theory_new": "Teoría Nueva",
                        "review": "Repaso",
                        "creative": "Creativo",
                        "coding": "Programación",
                        "math": "Matemáticas",
                    }.get(x, x),
                    help="¿Qué tipo de actividad realizaste?",
                )

            with type_col2:
                difficulty = st.selectbox(
                    "Dificultad Intentada",
                    options=[d.value for d in DifficultyEnum],
                    index=1,  # MEDIUM por defecto
                    format_func=lambda x: {
                        "EASY": "EASY — Configuración, lectura",
                        "MEDIUM": "MEDIUM — Lógica, ejercicios estándar",
                        "HARD": "HARD — Problemas complejos, demos",
                        "EPIC": "EPIC — Investigación, arquitectura",
                    }.get(x, x),
                )

            st.divider()

            # ── Métricas de rendimiento ──
            st.markdown("**Métricas de Rendimiento (post-sesión)**")

            perf_col1, perf_col2 = st.columns(2)

            with perf_col1:
                focus_score = st.slider(
                    "Focus Score",
                    min_value=1,
                    max_value=10,
                    value=5,
                    help="1 = Imposible concentrarme, 10 = Focus láser.",
                )
                comprehension_rate = st.slider(
                    "Comprensión (%)",
                    min_value=0,
                    max_value=100,
                    value=70,
                    step=5,
                    help="¿Cuánto entendiste del material trabajado?",
                )

            with perf_col2:
                flow_state = st.toggle(
                    "Estado de Flow",
                    value=False,
                    help="¿Entraste en ese estado de concentración profunda donde perdiste la noción del tiempo?",
                )
                interruptions = st.number_input(
                    "Interrupciones",
                    min_value=0,
                    max_value=50,
                    value=0,
                    help="Número de veces que te distrajiste o te interrumpieron.",
                )

            st.divider()

            submitted = st.form_submit_button(
                "Registrar Sesión",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            with Session(engine) as session:
                try:
                    # Verificar que exista DailyBiometrics para la fecha
                    bio_record = session.exec(
                        select(DailyBiometrics).where(
                            DailyBiometrics.date == session_date
                        )
                    ).first()

                    if bio_record is None:
                        # Crear registro mínimo para la fecha
                        bio_record = DailyBiometrics(date=session_date)
                        session.add(bio_record)
                        session.commit()

                    # Obtener ICD del día para snapshot
                    icd_at_start = bio_record.icd_score

                    # Crear hora de inicio y fin
                    start_dt = datetime.combine(session_date, start_time)
                    end_dt = start_dt + timedelta(minutes=duration_min)

                    # Crear sesión
                    new_session = StudySession(
                        date=session_date,
                        start_time=start_dt,
                        end_time=end_dt,
                        duration_min=duration_min,
                        task_type=task_type,
                        difficulty_attempted=difficulty,
                        focus_score=focus_score,
                        comprehension_rate=comprehension_rate,
                        flow_state=flow_state,
                        interruptions=interruptions,
                        icd_at_start=icd_at_start,
                    )
                    session.add(new_session)
                    session.commit()

                    st.success(
                        f"Sesión registrada: {task_type.replace('_', ' ').title()} "
                        f"({duration_min} min, Focus: {focus_score}/10"
                        + (f", ICD: {icd_at_start:.0f}" if icd_at_start else "")
                        + ")"
                    )

                    if flow_state:
                        st.balloons()
                        st.markdown("**Estado de Flow alcanzado.**")

                except Exception as e:
                    st.error(f"Error al registrar sesión: {e}")

    # ============================================================
    # TAB 2: Historial
    # ============================================================

    with tab_history:
        st.subheader("Historial de Sesiones")

        with Session(engine) as session:
            recent = get_recent_sessions(session, limit=50)

        if recent:
            # Estadísticas rápidas
            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
            with stat_col1:
                st.metric("Total Sesiones", len(recent))
            with stat_col2:
                total_min = sum(s.duration_min for s in recent if s.duration_min)
                st.metric("Tiempo Total", f"{total_min // 60}h {total_min % 60}m")
            with stat_col3:
                avg_focus = sum(
                    s.focus_score for s in recent if s.focus_score
                ) / max(1, sum(1 for s in recent if s.focus_score))
                st.metric("Focus Medio", f"{avg_focus:.1f}/10")
            with stat_col4:
                flow_count = sum(1 for s in recent if s.flow_state)
                st.metric("Sesiones Flow", flow_count)

            st.divider()
            render_session_table(recent)
        else:
            st.info("No hay sesiones registradas todavía.")

    # ============================================================
    # TAB 3: Retención 24h
    # ============================================================

    with tab_retention:
        st.subheader("Evaluación de Retención (24h)")
        st.caption(
            "Evalúa cuánto retienes del material de sesiones anteriores. "
            "Esto es clave para el lag analysis (tarea 3.7)."
        )

        with Session(engine) as session:
            # Buscar sesiones de ayer sin retención 24h
            yesterday = date.today() - timedelta(days=1)
            stmt = (
                select(StudySession)
                .where(StudySession.date == yesterday)
                .where(StudySession.retention_24h.is_(None))
            )
            pending_sessions = list(session.exec(stmt).all())

        if not pending_sessions:
            st.info(
                "No hay sesiones pendientes de evaluación de retención. "
                "Las sesiones de ayer ya fueron evaluadas o no existen."
            )
        else:
            st.markdown(f"**{len(pending_sessions)} sesiones de ayer pendientes de evaluación:**")

            for sess in pending_sessions:
                with st.form(f"retention_{sess.session_id}"):
                    st.markdown(
                        f"**{(sess.task_type or '—').replace('_', ' ').title()}** "
                        f"— {sess.duration_min} min "
                        f"(Focus: {sess.focus_score}/10, "
                        f"Comprensión: {sess.comprehension_rate}%)"
                    )

                    retention = st.slider(
                        "¿Cuánto recuerdas hoy? (%)",
                        min_value=0,
                        max_value=100,
                        value=50,
                        step=5,
                        key=f"ret_slider_{sess.session_id}",
                    )

                    if st.form_submit_button("Guardar Retención"):
                        with Session(engine) as db_session:
                            record = db_session.exec(
                                select(StudySession).where(
                                    StudySession.session_id == sess.session_id
                                )
                            ).first()
                            if record:
                                record.retention_24h = retention
                                db_session.commit()
                                st.success(f"Retención guardada: {retention}%")
                                st.rerun()
