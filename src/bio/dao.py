"""
Data Access Object (DAO) - Módulo Bio-Adaptabilidad

Funciones de acceso a datos que integran el cálculo automático de métricas derivadas
al insertar o actualizar registros de DailyBiometrics.

Referencia: docs/TAREAS.md § 3.3.1

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

from datetime import date as date_type
from typing import Any, Dict, Optional

from sqlmodel import Session, select

from src.bio.metrics import compute_derived_metrics
from src.bio.models import DailyBiometrics


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
