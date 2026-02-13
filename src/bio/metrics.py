"""
Cálculo de Métricas Derivadas - Módulo Bio-Adaptabilidad

Funciones para calcular métricas derivadas automáticamente al insertar/actualizar
registros de DailyBiometrics:
- ln_rmssd: Logaritmo natural de hrv_rmssd
- hrv_baseline_7d: Media Móvil Exponencial (EMA) de 7 días de ln_rmssd
- sleep_consistency: Desviación estándar de la hora de dormir (ventana 7 días)

Referencia: docs/TAREAS.md § 3.3.1

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

import math
from datetime import date as date_type, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from src.bio.models import DailyBiometrics


def compute_ln_rmssd(hrv_rmssd: Optional[float]) -> Optional[float]:
    """
    Calcula ln(hrv_rmssd) si el valor es válido.

    La HRV sigue distribución log-normal; ln() la normaliza para análisis.
    
    Args:
        hrv_rmssd: Valor de HRV RMSSD en milisegundos
        
    Returns:
        Logaritmo natural del HRV RMSSD, o None si el valor no es válido
    """
    if hrv_rmssd is not None and hrv_rmssd > 0:
        return math.log(hrv_rmssd)
    return None


def compute_hrv_baseline_7d(
    session: Session,
    date: date_type,
    ln_rmssd: Optional[float]
) -> Optional[float]:
    """
    Calcula la Media Móvil Exponencial (EMA) de 7 días de ln_rmssd.

    Consulta los últimos 7 días de registros y calcula EMA con span=7.
    El baseline se adapta gradualmente a cambios en el fitness del usuario.
    
    Args:
        session: Sesión de SQLModel para consultar la base de datos
        date: Fecha del registro actual
        ln_rmssd: Valor de ln_rmssd del día actual (puede ser None)
        
    Returns:
        Valor de EMA (baseline del día actual), o None si no hay suficientes datos
    """
    # Calcular fecha límite (7 días antes del día actual)
    date_limit = date - timedelta(days=7)
    
    # Consultar registros de los últimos 7 días (incluyendo el día actual)
    statement = select(DailyBiometrics).where(
        DailyBiometrics.date <= date,
        DailyBiometrics.date > date_limit
    ).order_by(DailyBiometrics.date.asc())
    
    records = session.exec(statement).all()
    
    if not records:
        return None
    
    # Extraer valores de ln_rmssd válidos (no None)
    # Primero, agregar valores históricos de la BD
    ln_values = []
    dates = []
    current_in_db = False
    
    for record in records:
        # Si es el registro actual, marcar que está en la BD
        if record.date == date:
            current_in_db = True
            # Si tiene ln_rmssd en la BD, usarlo; si no, usar el valor pasado como parámetro
            if record.ln_rmssd is not None:
                ln_values.append(record.ln_rmssd)
                dates.append(record.date)
            elif ln_rmssd is not None:
                ln_values.append(ln_rmssd)
                dates.append(record.date)
        # Si no es el actual, usar el ln_rmssd guardado en la BD
        elif record.ln_rmssd is not None:
            ln_values.append(record.ln_rmssd)
            dates.append(record.date)
    
    # Si el registro actual no está en la BD pero tenemos ln_rmssd, agregarlo
    if not current_in_db and ln_rmssd is not None:
        ln_values.append(ln_rmssd)
        dates.append(date)
    
    # Si no hay suficientes valores válidos, retornar None
    if len(ln_values) < 2:
        return None
    
    # Calcular EMA con span=7 usando pandas
    series = pd.Series(ln_values, index=dates)
    ema = series.ewm(span=7, adjust=False).mean()
    
    # Retornar el último valor de la EMA (baseline del día actual)
    return float(ema.iloc[-1])


def _time_to_minutes(time_str: Optional[str]) -> Optional[int]:
    """
    Convierte formato "HH:MM" a minutos desde medianoche.
    
    Args:
        time_str: Hora en formato "HH:MM" (ej: "02:17", "23:07")
        
    Returns:
        Minutos desde medianoche, o None si el formato es inválido
    """
    if time_str is None:
        return None
    
    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            return None
        hours = int(parts[0])
        minutes = int(parts[1])
        
        # Validar rango (0-23 horas, 0-59 minutos)
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            return None
        
        return hours * 60 + minutes
    except (ValueError, AttributeError):
        return None


def compute_sleep_consistency(
    session: Session,
    date: date_type,
    sleep_start_time: Optional[str]
) -> Optional[float]:
    """
    Calcula la desviación estándar de la hora de dormir (ventana 7 días).

    Mide la regularidad circadiana: valores bajos indican horarios consistentes,
    valores altos indican irregularidad en los horarios de sueño.
    
    Args:
        session: Sesión de SQLModel para consultar la base de datos
        date: Fecha del registro actual
        sleep_start_time: Hora de inicio del sueño del día actual (formato "HH:MM")
        
    Returns:
        Desviación estándar en minutos, o None si no hay suficientes datos
    """
    # Calcular fecha límite (7 días antes del día actual)
    date_limit = date - timedelta(days=7)
    
    # Consultar registros de los últimos 7 días (incluyendo el día actual)
    statement = select(DailyBiometrics).where(
        DailyBiometrics.date <= date,
        DailyBiometrics.date > date_limit
    ).order_by(DailyBiometrics.date.asc())
    
    records = session.exec(statement).all()
    
    if not records:
        return None
    
    # Extraer valores de sleep_start_time válidos
    sleep_times_minutes = []
    current_in_db = False
    
    for record in records:
        # Si es el registro actual, marcar que está en la BD
        if record.date == date:
            current_in_db = True
            # Si tiene sleep_start_time en la BD, usarlo; si no, usar el valor pasado como parámetro
            if record.sleep_start_time is not None:
                minutes = _time_to_minutes(record.sleep_start_time)
                if minutes is not None:
                    sleep_times_minutes.append(minutes)
            elif sleep_start_time is not None:
                minutes = _time_to_minutes(sleep_start_time)
                if minutes is not None:
                    sleep_times_minutes.append(minutes)
        # Si no es el actual, usar el sleep_start_time guardado en la BD
        elif record.sleep_start_time is not None:
            minutes = _time_to_minutes(record.sleep_start_time)
            if minutes is not None:
                sleep_times_minutes.append(minutes)
    
    # Si el registro actual no está en la BD pero tenemos sleep_start_time, agregarlo
    if not current_in_db and sleep_start_time is not None:
        minutes = _time_to_minutes(sleep_start_time)
        if minutes is not None:
            sleep_times_minutes.append(minutes)
    
    # Necesitamos al menos 2 valores para calcular desviación estándar
    if len(sleep_times_minutes) < 2:
        return None
    
    # Calcular desviación estándar
    std_dev = float(np.std(sleep_times_minutes))
    
    return std_dev


def compute_derived_metrics(
    session: Session,
    record: DailyBiometrics
) -> DailyBiometrics:
    """
    Calcula todas las métricas derivadas para un registro de DailyBiometrics.

    Esta función debe llamarse antes de insertar o actualizar un registro
    para garantizar que las métricas derivadas estén calculadas.
    
    Args:
        session: Sesión de SQLModel para consultar datos históricos
        record: Registro de DailyBiometrics a procesar
        
    Returns:
        El mismo objeto con las métricas derivadas calculadas y asignadas
    """
    # 1. Calcular ln_rmssd
    record.ln_rmssd = compute_ln_rmssd(record.hrv_rmssd)
    
    # 2. Calcular hrv_baseline_7d (requiere consultar datos históricos)
    record.hrv_baseline_7d = compute_hrv_baseline_7d(
        session=session,
        date=record.date,
        ln_rmssd=record.ln_rmssd
    )
    
    # 3. Calcular sleep_consistency (requiere consultar datos históricos)
    record.sleep_consistency = compute_sleep_consistency(
        session=session,
        date=record.date,
        sleep_start_time=record.sleep_start_time
    )
    
    return record
