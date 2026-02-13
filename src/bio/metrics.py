
"""
Cálculo de Métricas Derivadas - Módulo Bio-Adaptabilidad

Funciones para calcular métricas derivadas automáticamente al insertar/actualizar
registros de DailyBiometrics:
- ln_rmssd: Logaritmo natural de hrv_rmssd
- hrv_baseline_7d: Media Móvil Exponencial (EMA) de 7 días de ln_rmssd
- sleep_consistency: Desviación estándar de la hora de dormir (ventana 7 días)
- icd_score: Índice Cognitivo Diario (score 0-100 combinando métricas biológicas y subjetivas)

Referencias:
- docs/TAREAS.md § 3.3.1 (métricas derivadas básicas)
- docs/TAREAS.md § 3.4.1 (cálculo del ICD)

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

import math
from datetime import date as date_type, timedelta
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from src.bio.models import DailyBiometrics, MoodEnum


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


def compute_sleep_quality_baseline(
    session: Session,
    date: date_type,
    sleep_quality: Optional[int]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calcula la media y desviación estándar de sleep_quality en ventana histórica.

    Consulta los últimos 14 días de registros para calcular estadísticas
    que se usarán como baseline para el cálculo de Z-score.

    Args:
        session: Sesión de SQLModel para consultar la base de datos
        date: Fecha del registro actual
        sleep_quality: Valor de sleep_quality del día actual (puede ser None)

    Returns:
        Tupla (media, std_dev) de sleep_quality histórica, o (None, None) si no hay suficientes datos
    """
    # Calcular fecha límite (14 días antes del día actual para tener más datos)
    date_limit = date - timedelta(days=14)

    # Consultar registros de los últimos 14 días (incluyendo el día actual)
    statement = select(DailyBiometrics).where(
        DailyBiometrics.date <= date,
        DailyBiometrics.date > date_limit
    ).order_by(DailyBiometrics.date.asc())

    records = session.exec(statement).all()

    if not records:
        return (None, None)

    # Extraer valores de sleep_quality válidos (no None, en rango 0-100)
    sleep_quality_values = []
    current_in_db = False

    for record in records:
        # Si es el registro actual, marcar que está en la BD
        if record.date == date:
            current_in_db = True
            # Si tiene sleep_quality en la BD, usarlo; si no, usar el valor pasado como parámetro
            if record.sleep_quality is not None and 0 <= record.sleep_quality <= 100:
                sleep_quality_values.append(record.sleep_quality)
            elif sleep_quality is not None and 0 <= sleep_quality <= 100:
                sleep_quality_values.append(sleep_quality)
        # Si no es el actual, usar el sleep_quality guardado en la BD
        elif record.sleep_quality is not None and 0 <= record.sleep_quality <= 100:
            sleep_quality_values.append(record.sleep_quality)

    # Si el registro actual no está en la BD pero tenemos sleep_quality, agregarlo
    if not current_in_db and sleep_quality is not None and 0 <= sleep_quality <= 100:
        sleep_quality_values.append(sleep_quality)

    # Necesitamos al menos 2 valores para calcular media y desviación estándar
    if len(sleep_quality_values) < 2:
        return (None, None)

    # Calcular media y desviación estándar
    mean = float(np.mean(sleep_quality_values))
    # ddof=0 para población completa
    std_dev = float(np.std(sleep_quality_values, ddof=0))

    return (mean, std_dev)


def compute_z_score(
    value: Optional[float],
    mean: Optional[float],
    std_dev: Optional[float]
) -> float:
    """
    Calcula el Z-score de un valor respecto a una distribución.

    Z-score indica cuántas desviaciones estándar se aleja el valor de la media.
    Maneja casos edge como std_dev = 0 o valores None.

    Args:
        value: Valor a normalizar (puede ser None)
        mean: Media de la distribución (puede ser None)
        std_dev: Desviación estándar de la distribución (puede ser None)

    Returns:
        Z-score calculado. Retorna 0.0 si no se puede calcular (valores None o std_dev = 0)
    """
    # Si alguno de los valores es None, retornar 0.0 (neutral)
    if value is None or mean is None or std_dev is None:
        return 0.0

    # Si la desviación estándar es 0 o muy pequeña, retornar 0.0 (no hay variabilidad)
    if std_dev < 1e-10:
        return 0.0

    # Calcular Z-score: (valor - media) / desviación_estándar
    z_score = (value - mean) / std_dev

    return float(z_score)


def calculate_icd(
    session: Session,
    record: DailyBiometrics,
    weights: Optional[Dict[str, float]] = None
) -> Optional[float]:
    """
    Calcula el Índice Cognitivo Diario (ICD) combinando métricas biológicas y subjetivas.

    El ICD es un score único 0-100 que determina el "ancho de banda cognitivo" del día.
    Combina:
    - Métricas biológicas (HRV, sueño) mediante Z-scores respecto a baseline personal
    - Métricas subjetivas (energía, claridad mental, recursos corporales) mediante normalización min-max
    - Estado de ánimo mediante bonus/penalización

    Fórmula:
        ICD_raw = w1·Z(ln_rmssd) + w2·Z(sleep_quality) + w3·body_resources_norm
                + w4·energy_norm + w5·mental_clarity_norm + w6·mood_bonus

        ICD = clip(50 + (ICD_raw * 16.67), 0, 100)

    Pesos por defecto (hipótesis inicial a validar con datos):
    - ln_rmssd: 0.25 (métrica biológica clave)
    - sleep_quality: 0.20 (calidad de sueño)
    - body_resources: 0.20 (recursos corporales Suunto)
    - energy: 0.15 (energía física percibida)
    - mental_clarity: 0.10 (claridad mental)
    - mood: 0.10 (estado de ánimo)

    Referencia: docs/TAREAS.md § 3.4.1

    Args:
        session: Sesión de SQLModel para consultar datos históricos (necesario para Z-scores)
        record: Registro de DailyBiometrics con las métricas del día
        weights: Diccionario opcional con pesos personalizados. Si es None, usa pesos por defecto.
                 Claves: "ln_rmssd", "sleep_quality", "body_resources", "energy", "mental_clarity", "mood"

    Returns:
        Valor del ICD en rango 0-100, o None si no hay suficientes datos para calcular
    """
    # Pesos por defecto según especificación
    DEFAULT_WEIGHTS = {
        "ln_rmssd": 0.25,
        "sleep_quality": 0.20,
        "body_resources": 0.20,
        "energy": 0.15,
        "mental_clarity": 0.10,
        "mood": 0.10
    }

    # Usar pesos personalizados si se proporcionan, sino usar los por defecto
    if weights is None:
        weights = DEFAULT_WEIGHTS
    else:
        # Combinar con defaults para asegurar que todos los pesos estén definidos
        final_weights = DEFAULT_WEIGHTS.copy()
        final_weights.update(weights)
        weights = final_weights

    # Validar que los pesos sumen aproximadamente 1.0 (con tolerancia pequeña)
    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > 0.01:
        raise ValueError(
            f"Los pesos deben sumar 1.0, pero suman {total_weight:.3f}. "
            f"Pesos proporcionados: {weights}"
        )

    # ========================================================================
    # 1. CALCULAR Z-SCORES PARA MÉTRICAS BIOLÓGICAS
    # ========================================================================

    # Z-score para ln_rmssd
    z_ln_rmssd = 0.0
    if record.ln_rmssd is not None and record.hrv_baseline_7d is not None:
        # Necesitamos calcular la desviación estándar histórica de ln_rmssd
        date_limit = record.date - timedelta(days=14)
        statement = select(DailyBiometrics).where(
            DailyBiometrics.date <= record.date,
            DailyBiometrics.date > date_limit,
            DailyBiometrics.ln_rmssd.isnot(None)
        ).order_by(DailyBiometrics.date.asc())

        historical_records = session.exec(statement).all()

        if historical_records:
            # Extraer valores históricos de ln_rmssd
            ln_rmssd_values = [
                r.ln_rmssd for r in historical_records if r.ln_rmssd is not None]

            # Si tenemos suficientes datos, calcular std_dev
            if len(ln_rmssd_values) >= 2:
                mean_ln_rmssd = record.hrv_baseline_7d  # Usar el baseline como media
                std_dev_ln_rmssd = float(np.std(ln_rmssd_values, ddof=0))
                z_ln_rmssd = compute_z_score(
                    record.ln_rmssd, mean_ln_rmssd, std_dev_ln_rmssd)

    # Z-score para sleep_quality
    z_sleep_quality = 0.0
    if record.sleep_quality is not None:
        mean_sleep, std_dev_sleep = compute_sleep_quality_baseline(
            session=session,
            date=record.date,
            sleep_quality=record.sleep_quality
        )
        if mean_sleep is not None and std_dev_sleep is not None:
            z_sleep_quality = compute_z_score(
                float(record.sleep_quality),
                mean_sleep,
                std_dev_sleep
            )

    # ========================================================================
    # 2. NORMALIZACIÓN MIN-MAX PARA MÉTRICAS SUBJETIVAS (0-1)
    # ========================================================================

    # body_resources: ya está en rango 0-100, normalizar a 0-1
    body_resources_norm = 0.0
    if record.body_resources is not None:
        body_resources_norm = float(record.body_resources) / 100.0
        # Asegurar que esté en rango [0, 1]
        body_resources_norm = max(0.0, min(1.0, body_resources_norm))

    # energy_level: está en rango 1-10, normalizar a 0-1
    energy_norm = 0.0
    if record.energy_level is not None:
        energy_norm = (float(record.energy_level) - 1.0) / 9.0
        # Asegurar que esté en rango [0, 1]
        energy_norm = max(0.0, min(1.0, energy_norm))

    # mental_clarity: está en rango 1-10, normalizar a 0-1
    mental_clarity_norm = 0.0
    if record.mental_clarity is not None:
        mental_clarity_norm = (float(record.mental_clarity) - 1.0) / 9.0
        # Asegurar que esté en rango [0, 1]
        mental_clarity_norm = max(0.0, min(1.0, mental_clarity_norm))

    # ========================================================================
    # 3. MOOD BONUS
    # ========================================================================

    mood_bonus = 0.0
    if record.mood is not None:
        mood_lower = record.mood.lower().strip()
        if mood_lower == MoodEnum.FOCUSED.value:
            mood_bonus = 1.0
        elif mood_lower == MoodEnum.NEUTRAL.value:
            mood_bonus = 0.0
        elif mood_lower == MoodEnum.ANXIOUS.value:
            mood_bonus = -0.3
        elif mood_lower == MoodEnum.TIRED.value:
            mood_bonus = -0.5
        # Si el mood no coincide con ningún valor conocido, mantener 0.0

    # ========================================================================
    # 4. COMBINACIÓN CON PESOS
    # ========================================================================

    icd_raw = (
        weights["ln_rmssd"] * z_ln_rmssd +
        weights["sleep_quality"] * z_sleep_quality +
        weights["body_resources"] * body_resources_norm +
        weights["energy"] * energy_norm +
        weights["mental_clarity"] * mental_clarity_norm +
        weights["mood"] * mood_bonus
    )

    # ========================================================================
    # 5. ESCALADO A RANGO 0-100 CON CLIPPING
    # ========================================================================

    # Estrategia: Transformar ICD_raw (que puede estar en rango aproximadamente -3 a +3)
    # a rango 0-100 usando transformación lineal centrada en 50
    # Factor de escala: 16.67 permite que un ICD_raw de 3.0 se convierta en ~100
    # y un ICD_raw de -3.0 se convierta en ~0
    icd_score = 50.0 + (icd_raw * 16.67)

    # Aplicar clipping para asegurar que esté en rango [0, 100]
    icd_score = max(0.0, min(100.0, icd_score))

    return float(icd_score)


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

    # 4. Calcular icd_score (requiere todas las métricas anteriores y consultar datos históricos)
    record.icd_score = calculate_icd(
        session=session,
        record=record
    )

    return record
