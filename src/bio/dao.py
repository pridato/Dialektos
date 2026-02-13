"""
Data Access Object (DAO) - Módulo Bio-Adaptabilidad

Funciones de acceso a datos que integran el cálculo automático de métricas derivadas
al insertar o actualizar registros de DailyBiometrics y StudySession.

Referencia: docs/TAREAS.md § 3.3.1, § 3.6.1

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

import logging
from datetime import date as date_type, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from src.bio.metrics import compute_derived_metrics
from src.bio.models import DailyBiometrics, StudySession

logger = logging.getLogger(__name__)


def create_or_update_biometrics(
    session: Session,
    data: Dict[str, Any]
) -> DailyBiometrics:
    """
    Crea o actualiza un registro de DailyBiometrics con cálculo automático de métricas derivadas.

    Esta función:
    1. Busca si existe un registro para la fecha especificada
    2. Si existe, actualiza los campos proporcionados
    3. Si no existe, crea un nuevo registro
    4. Calcula automáticamente las métricas derivadas (ln_rmssd, hrv_baseline_7d, sleep_consistency)
    5. Guarda el registro en la base de datos
    
    Args:
        session: Sesión de SQLModel para acceder a la base de datos
        data: Diccionario con los datos del registro. Debe incluir 'date' como mínimo.
              Puede incluir cualquier campo de DailyBiometrics.
              
    Returns:
        El objeto DailyBiometrics creado o actualizado
        
    Raises:
        ValueError: Si no se proporciona el campo 'date' en data
    """
    if "date" not in data:
        raise ValueError("El campo 'date' es obligatorio en data")
    
    date = data["date"]
    
    # Buscar registro existente
    statement = select(DailyBiometrics).where(DailyBiometrics.date == date)
    existing_record = session.exec(statement).first()
    
    if existing_record:
        # Actualizar registro existente
        for key, value in data.items():
            if hasattr(existing_record, key):
                setattr(existing_record, key, value)
        record = existing_record
    else:
        # Crear nuevo registro
        record = DailyBiometrics(**data)
        session.add(record)
    
    # Calcular métricas derivadas antes de guardar
    # Esto requiere que el registro esté en la sesión para poder consultar datos históricos
    record = compute_derived_metrics(session=session, record=record)
    
    # Guardar cambios
    session.commit()
    session.refresh(record)
    
    return record


# ============================================================================
# StudySession DAO — Tarea 3.6.1
# ============================================================================


def create_study_session(
    session: Session,
    data: Dict[str, Any],
) -> StudySession:
    """
    Crea una nueva sesión de estudio con captura automática del ICD snapshot.

    Flujo:
    1. Valida que ``data`` contenga el campo ``date``.
    2. Consulta ``DailyBiometrics`` del día para obtener ``icd_score``.
    3. Asigna ``icd_at_start`` automáticamente (queda ``None`` si no hay biometrics).
    4. Inserta el registro en ``study_sessions``.

    Args:
        session: Sesión de SQLModel activa.
        data: Diccionario con los campos de ``StudySession``.
              Debe incluir ``date`` y ``start_time`` como mínimo.

    Returns:
        El objeto ``StudySession`` ya persistido (con ``session_id`` asignado).

    Raises:
        ValueError: Si ``date`` no está presente en *data*.
    """
    if "date" not in data:
        raise ValueError("El campo 'date' es obligatorio en data")

    target_date: date_type = data["date"]

    # --- Auto-enlace: capturar icd_at_start desde DailyBiometrics del día ---
    if "icd_at_start" not in data or data["icd_at_start"] is None:
        biometrics: Optional[DailyBiometrics] = session.exec(
            select(DailyBiometrics).where(DailyBiometrics.date == target_date)
        ).first()

        if biometrics is not None and biometrics.icd_score is not None:
            data["icd_at_start"] = biometrics.icd_score
        else:
            logger.warning(
                "No se encontró DailyBiometrics (o icd_score es None) para %s. "
                "icd_at_start quedará como None.",
                target_date,
            )

    study_session = StudySession(**data)
    session.add(study_session)
    session.commit()
    session.refresh(study_session)

    return study_session


def get_sessions_by_date(
    session: Session,
    date: date_type,
) -> List[StudySession]:
    """
    Devuelve todas las sesiones de estudio de un día concreto.

    Permite múltiples sesiones por día (mañana, tarde, noche).

    Args:
        session: Sesión de SQLModel activa.
        date: Fecha a consultar.

    Returns:
        Lista de ``StudySession`` ordenada por ``start_time`` ascendente.
    """
    statement = (
        select(StudySession)
        .where(StudySession.date == date)
        .order_by(StudySession.start_time.asc())
    )
    return list(session.exec(statement).all())


def get_recent_sessions(
    session: Session,
    days: int = 7,
) -> List[StudySession]:
    """
    Devuelve las sesiones de los últimos *days* días (incluido hoy).

    Útil para la tabla histórica del dashboard Streamlit.

    Args:
        session: Sesión de SQLModel activa.
        days: Número de días hacia atrás (por defecto 7).

    Returns:
        Lista de ``StudySession`` ordenada por fecha y hora descendente.
    """
    cutoff = date_type.today() - timedelta(days=days - 1)
    statement = (
        select(StudySession)
        .where(StudySession.date >= cutoff)
        .order_by(StudySession.date.desc(), StudySession.start_time.desc())
    )
    return list(session.exec(statement).all())
