"""
Página: Ingreso de Datos Fisiológicos (Suunto + Subjetivos + Confounders)

Formulario completo para registrar:
- Datos objetivos de Suunto (HRV, sueño, body resources)
- Datos subjetivos (energía, claridad mental, mood, motivación)
- Variables de confusión (cafeína, ejercicio, estrés)

Al guardar, calcula automáticamente métricas derivadas (ln_rmssd, baseline, ICD).

Referencia: docs/TAREAS.md § Módulo 4 — Ingreso de Datos Fisiológicos.

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict

import streamlit as st
from sqlmodel import Session, select

from src.bio.dao import create_or_update_biometrics
from src.bio.db import get_engine
from src.bio.models import (
    DailyBiometrics,
    DailyConfounders,
    ExerciseTypeEnum,
    MoodEnum,
)
from src.ui.components import COLORS, get_today_biometrics


def render_data_entry(engine: Any) -> None:
    """Renderiza la página de ingreso de datos fisiológicos con diseño moderno."""

    st.markdown("# Bio-Tracker")
    st.caption(
        "Registra tus datos subjetivos diarios. Ajusta los valores según tu estado actual. "
        "El ICD se calcula automáticamente al guardar."
    )

    # ── Selección de fecha ──
    selected_date = st.date_input(
        "Fecha del registro",
        value=date.today(),
        max_value=date.today(),
        min_value=date.today() - timedelta(days=30),
    )

    # ── Cargar datos existentes para la fecha ──
    with Session(engine) as session:
        stmt = select(DailyBiometrics).where(
            DailyBiometrics.date == selected_date
        )
        existing_bio = session.exec(stmt).first()

        stmt_conf = select(DailyConfounders).where(
            DailyConfounders.date == selected_date
        )
        existing_conf = session.exec(stmt_conf).first()

    if existing_bio:
        st.success(
            f"Datos existentes para {selected_date}. "
            "Los campos se han rellenado con los valores actuales."
        )

    st.divider()

    # ============================================================
    # FORMULARIO PRINCIPAL
    # ============================================================

    with st.form("biometrics_form", clear_on_submit=False):
        # ── Sección 1: Datos Objetivos (Suunto) ──
        st.subheader("Datos Objetivos (Suunto)")
        st.caption("Métricas de tu wearable Suunto.")

        obj_col1, obj_col2, obj_col3 = st.columns(3)

        with obj_col1:
            hrv_rmssd = st.number_input(
                "HRV RMSSD (ms)",
                min_value=0.0,
                max_value=300.0,
                value=float(existing_bio.hrv_rmssd) if existing_bio and existing_bio.hrv_rmssd else 0.0,
                step=0.1,
                help="HRV nocturna en milisegundos. Valores típicos: 20-100 ms.",
            )
            resting_hr = st.number_input(
                "FC Reposo (bpm)",
                min_value=30,
                max_value=120,
                value=existing_bio.resting_hr if existing_bio and existing_bio.resting_hr else 60,
                help="Frecuencia cardíaca en reposo.",
            )
            avg_hr_sleep = st.number_input(
                "FC Media Sueño (bpm)",
                min_value=30.0,
                max_value=120.0,
                value=float(existing_bio.avg_hr_sleep) if existing_bio and existing_bio.avg_hr_sleep else 55.0,
                step=0.1,
            )

        with obj_col2:
            sleep_total_min = st.number_input(
                "Sueño Total (min)",
                min_value=0,
                max_value=720,
                value=existing_bio.sleep_total_min if existing_bio and existing_bio.sleep_total_min else 420,
                help="Tiempo total de sueño en minutos.",
            )
            deep_sleep_min = st.number_input(
                "Sueño Profundo (min)",
                min_value=0,
                max_value=300,
                value=existing_bio.deep_sleep_min if existing_bio and existing_bio.deep_sleep_min else 90,
            )
            rem_sleep_min = st.number_input(
                "Sueño REM (min)",
                min_value=0,
                max_value=300,
                value=existing_bio.rem_sleep_min if existing_bio and existing_bio.rem_sleep_min else 80,
            )

        with obj_col3:
            light_sleep_min = st.number_input(
                "Sueño Ligero (min)",
                min_value=0,
                max_value=400,
                value=existing_bio.light_sleep_min if existing_bio and existing_bio.light_sleep_min else 200,
            )
            awake_min = st.number_input(
                "Despierto (min)",
                min_value=0,
                max_value=180,
                value=existing_bio.awake_min if existing_bio and existing_bio.awake_min else 30,
            )
            sleep_start_time = st.text_input(
                "Hora de Dormir (HH:MM)",
                value=existing_bio.sleep_start_time if existing_bio and existing_bio.sleep_start_time else "23:00",
                help="Formato 24h. Ej: 23:30, 00:15",
            )

        score_col1, score_col2, score_col3 = st.columns(3)

        with score_col1:
            sleep_quality = st.slider(
                "Calidad Sueño (Suunto)",
                min_value=0,
                max_value=100,
                value=existing_bio.sleep_quality if existing_bio and existing_bio.sleep_quality is not None else 70,
                help="Score de calidad de sueño de Suunto (0-100).",
            )
        with score_col2:
            body_resources = st.slider(
                "Body Resources",
                min_value=0,
                max_value=100,
                value=existing_bio.body_resources if existing_bio and existing_bio.body_resources is not None else 60,
                help="Índice integrado de recuperación de Suunto (0-100). Feature clave.",
            )
        with score_col3:
            training_load = st.number_input(
                "Carga Entrenamiento",
                min_value=0.0,
                max_value=500.0,
                value=float(existing_bio.training_load) if existing_bio and existing_bio.training_load else 0.0,
                step=0.1,
                help="Training load acumulado (TSB).",
            )

        st.divider()

        # ── Sección 2: Datos Subjetivos mejorados ──
        st.subheader("Autoevaluación Subjetiva")
        st.caption("¿Cómo te sientes hoy? Estas métricas son ortogonales entre sí.")

        # Sliders mejorados con diseño visual
        st.markdown("#### Nivel de Energía")
        energy_level = st.slider(
            f"Energía Física: {existing_bio.energy_level if existing_bio and existing_bio.energy_level else 5}/10",
            min_value=1,
            max_value=10,
            value=existing_bio.energy_level if existing_bio and existing_bio.energy_level else 5,
            help="1 = Agotado, 10 = Lleno de energía.",
            key="energy_slider",
        )
        
        st.markdown("#### Claridad Mental")
        mental_clarity = st.slider(
            f"Claridad Mental: {existing_bio.mental_clarity if existing_bio and existing_bio.mental_clarity else 5}/10",
            min_value=1,
            max_value=10,
            value=existing_bio.mental_clarity if existing_bio and existing_bio.mental_clarity else 5,
            help="1 = Niebla mental, 10 = Agudeza máxima.",
            key="clarity_slider",
        )
        
        st.markdown("#### Motivación")
        motivation = st.slider(
            f"Motivación para Estudiar: {existing_bio.motivation if existing_bio and existing_bio.motivation else 5}/10",
            min_value=1,
            max_value=10,
            value=existing_bio.motivation if existing_bio and existing_bio.motivation else 5,
            help="1 = Sin ganas, 10 = Muy motivado.",
            key="motivation_slider",
        )
        
        st.markdown("#### Fatiga Física")
        muscle_soreness = st.slider(
            f"Agujetas / Fatiga Física: {existing_bio.muscle_soreness if existing_bio and existing_bio.muscle_soreness else 3}/10",
            min_value=1,
            max_value=10,
            value=existing_bio.muscle_soreness if existing_bio and existing_bio.muscle_soreness else 3,
            help="1 = Sin dolor, 10 = Muy dolorido.",
            key="soreness_slider",
        )
        
        st.markdown("#### Estado de Ánimo")
        mood_options = [m.value for m in MoodEnum]
        current_mood_idx = 3  # neutral
        if existing_bio and existing_bio.mood:
            try:
                current_mood_idx = mood_options.index(existing_bio.mood)
            except ValueError:
                current_mood_idx = 3
        mood = st.selectbox(
            "Estado de Ánimo",
            options=mood_options,
            index=current_mood_idx,
            format_func=lambda x: {
                "focused": "🎯 Enfocado (Focused)",
                "anxious": "😰 Ansioso (Anxious)",
                "tired": "😴 Cansado (Tired)",
                "neutral": "😐 Neutral",
            }.get(x, x),
            help="Estado emocional general del día.",
        )

        st.divider()

        # ── Sección 3: Variables de Confusión (Confounders) ──
        st.subheader("Variables de Confusión")
        st.caption(
            "Sin esto, el análisis de correlación puede ser espurio. "
            "Controla factores externos que afectan al rendimiento."
        )

        conf_col1, conf_col2 = st.columns(2)

        with conf_col1:
            caffeine_mg = st.number_input(
                "Cafeína (mg)",
                min_value=0,
                max_value=600,
                value=existing_conf.caffeine_mg if existing_conf and existing_conf.caffeine_mg else 0,
                step=47,
                help="Café ~95mg, Té ~47mg, Red Bull ~80mg.",
            )
            screen_time_pre_sleep = st.number_input(
                "Pantalla pre-sueño (min)",
                min_value=0,
                max_value=300,
                value=existing_conf.screen_time_pre_sleep if existing_conf and existing_conf.screen_time_pre_sleep else 30,
                help="Minutos de pantalla antes de dormir.",
            )
            meals_quality = st.slider(
                "Calidad Alimentación",
                min_value=1,
                max_value=5,
                value=existing_conf.meals_quality if existing_conf and existing_conf.meals_quality else 3,
                help="1 = Muy mala, 5 = Excelente.",
            )

        with conf_col2:
            social_stress = st.slider(
                "Estrés Social/Emocional",
                min_value=1,
                max_value=10,
                value=existing_conf.social_stress if existing_conf and existing_conf.social_stress else 3,
                help="1 = Tranquilo, 10 = Muy estresado.",
            )
            exercise_options = [e.value for e in ExerciseTypeEnum]
            current_exercise_idx = 0
            if existing_conf and existing_conf.exercise_type:
                try:
                    current_exercise_idx = exercise_options.index(existing_conf.exercise_type)
                except ValueError:
                    current_exercise_idx = 0
            exercise_type = st.selectbox(
                "Tipo de Ejercicio",
                options=exercise_options,
                index=current_exercise_idx,
                format_func=lambda x: {
                    "none": "Ninguno",
                    "light": "Ligero (caminar, yoga)",
                    "moderate": "Moderado (running suave, gym)",
                    "intense": "Intenso (HIIT, competición)",
                }.get(x, x),
            )
            exercise_min = st.number_input(
                "Duración Ejercicio (min)",
                min_value=0,
                max_value=300,
                value=existing_conf.exercise_min if existing_conf and existing_conf.exercise_min else 0,
            )

        st.markdown("#### Notas del día")
        notes = st.text_area(
            "Notas adicionales",
            value=existing_conf.notes if existing_conf and existing_conf.notes else "",
            placeholder="Escribe cualquier contexto adicional sobre tu estado actual...\n\nEjemplos:\n- Examen mañana\n- Viaje\n- Dormí en sitio nuevo\n- Estrés laboral",
            max_chars=500,
            height=120,
            help="Contexto cualitativo que puede afectar tus métricas.",
        )

        st.divider()

        # ── Botón de guardar mejorado ──
        submitted = st.form_submit_button(
            "💾 Calcular ICD y Sincronizar Suunto",
            type="primary",
            use_container_width=True,
        )

    # ============================================================
    # PROCESAMIENTO AL GUARDAR
    # ============================================================

    if submitted:
        with Session(engine) as session:
            try:
                # Construir diccionario de datos biométricos
                bio_data: Dict[str, Any] = {
                    "date": selected_date,
                    "hrv_rmssd": hrv_rmssd if hrv_rmssd > 0 else None,
                    "resting_hr": resting_hr,
                    "avg_hr_sleep": avg_hr_sleep,
                    "sleep_total_min": sleep_total_min,
                    "deep_sleep_min": deep_sleep_min,
                    "rem_sleep_min": rem_sleep_min,
                    "light_sleep_min": light_sleep_min,
                    "awake_min": awake_min,
                    "sleep_start_time": sleep_start_time if sleep_start_time else None,
                    "sleep_quality": sleep_quality,
                    "body_resources": body_resources,
                    "training_load": training_load if training_load > 0 else None,
                    "energy_level": energy_level,
                    "mental_clarity": mental_clarity,
                    "mood": mood,
                    "motivation": motivation,
                    "muscle_soreness": muscle_soreness,
                }

                # Guardar biometrics (con cálculo automático de derivadas)
                record = create_or_update_biometrics(session, bio_data)

                # Guardar confounders
                existing_conf_db = session.exec(
                    select(DailyConfounders).where(
                        DailyConfounders.date == selected_date
                    )
                ).first()

                if existing_conf_db:
                    existing_conf_db.caffeine_mg = caffeine_mg if caffeine_mg > 0 else None
                    existing_conf_db.screen_time_pre_sleep = screen_time_pre_sleep
                    existing_conf_db.meals_quality = meals_quality
                    existing_conf_db.social_stress = social_stress
                    existing_conf_db.exercise_type = exercise_type
                    existing_conf_db.exercise_min = exercise_min if exercise_min > 0 else None
                    existing_conf_db.notes = notes if notes.strip() else None
                else:
                    new_conf = DailyConfounders(
                        date=selected_date,
                        caffeine_mg=caffeine_mg if caffeine_mg > 0 else None,
                        screen_time_pre_sleep=screen_time_pre_sleep,
                        meals_quality=meals_quality,
                        social_stress=social_stress,
                        exercise_type=exercise_type,
                        exercise_min=exercise_min if exercise_min > 0 else None,
                        notes=notes if notes.strip() else None,
                    )
                    session.add(new_conf)

                session.commit()

                # Mostrar resultado
                st.success(f"Datos guardados para {selected_date}.")

                if record.icd_score is not None:
                    from src.bio.decision import get_strategy
                    strat = get_strategy(record.icd_score)
                    st.balloons()
                    st.markdown(
                        f"""
                        ### {strat.emoji} ICD Calculado: **{record.icd_score:.1f}** — {strat.name}

                        {strat.description}
                        """,
                    )
                else:
                    st.warning(
                        "ICD no calculado. Se necesitan más días de datos "
                        "para calcular baselines (mínimo 2 días)."
                    )

            except Exception as e:
                st.error(f"Error al guardar: {e}")
