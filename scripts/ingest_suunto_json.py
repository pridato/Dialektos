"""
Script de Ingesta de Datos Suunto desde JSON

Lee el archivo JSON de datos Suunto y los inserta en la base de datos,
calculando automáticamente las métricas derivadas (ln_rmssd, hrv_baseline_7d,
sleep_consistency, icd_score).

Uso:
    python scripts/ingest_suunto_json.py
    O: PYTHONPATH=. python scripts/ingest_suunto_json.py

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations
from src.bio.db import get_engine
from src.bio.dao import create_or_update_biometrics
from sqlmodel import Session

import json
import sys
from datetime import date as date_type
from pathlib import Path
from typing import Any, Dict

# Añadir el directorio raíz al path para imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def parse_date(date_str: str) -> date_type:
    """
    Convierte una fecha en formato string (YYYY-MM-DD) a objeto date.

    Args:
        date_str: Fecha en formato "YYYY-MM-DD"

    Returns:
        Objeto date

    Raises:
        ValueError: Si el formato de fecha es inválido
    """
    try:
        year, month, day = map(int, date_str.split("-"))
        return date_type(year, month, day)
    except (ValueError, AttributeError) as e:
        raise ValueError(
            f"Formato de fecha inválido: {date_str}. Debe ser YYYY-MM-DD") from e


def normalize_json_data(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza los datos del JSON para que coincidan con el esquema de DailyBiometrics.

    Convierte:
    - 'date' de string a objeto date
    - Maneja campos opcionales (None si no existen)
    - Asegura que los tipos sean correctos

    Args:
        json_data: Diccionario con datos del JSON

    Returns:
        Diccionario normalizado listo para insertar en DailyBiometrics
    """
    normalized = {}

    # Fecha es obligatoria
    if "date" not in json_data:
        raise ValueError("El campo 'date' es obligatorio en los datos JSON")

    normalized["date"] = parse_date(json_data["date"])

    # Campos objetivos (Suunto) - todos opcionales
    objective_fields = [
        "hrv_rmssd",
        "resting_hr",
        "avg_hr_sleep",
        "sleep_total_min",
        "deep_sleep_min",
        "rem_sleep_min",
        "light_sleep_min",
        "awake_min",
        "sleep_start_time",
        "sleep_quality",
        "body_resources",
        "training_load"
    ]

    for field in objective_fields:
        if field in json_data and json_data[field] is not None:
            normalized[field] = json_data[field]

    # Campos subjetivos (Usuario) - todos opcionales
    subjective_fields = [
        "energy_level",
        "mental_clarity",
        "mood",
        "motivation",
        "muscle_soreness"
    ]

    for field in subjective_fields:
        if field in json_data and json_data[field] is not None:
            normalized[field] = json_data[field]

    return normalized


def ingest_suunto_json(
    json_path: Path,
    db_path: Path | None = None
) -> None:
    """
    Ingesta todos los datos del archivo JSON de Suunto en la base de datos.

    Lee el archivo JSON, normaliza cada registro y lo inserta/actualiza en la BD
    usando el DAO, que calcula automáticamente las métricas derivadas.

    Args:
        json_path: Ruta al archivo JSON con los datos de Suunto
        db_path: Ruta opcional a la base de datos. Si es None, usa la ruta por defecto.

    Raises:
        FileNotFoundError: Si el archivo JSON no existe
        ValueError: Si el JSON tiene formato inválido o datos incorrectos
    """
    # Verificar que el archivo existe
    if not json_path.exists():
        raise FileNotFoundError(f"El archivo JSON no existe: {json_path}")

    # Leer el archivo JSON
    print(f"Leyendo archivo JSON: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("El JSON debe contener una lista de registros")

    print(f"Encontrados {len(data)} registros en el JSON")

    # Conectar a la base de datos
    engine = get_engine(db_path)

    # Procesar cada registro
    inserted_count = 0
    updated_count = 0
    error_count = 0

    with Session(engine) as session:
        for idx, json_record in enumerate(data, start=1):
            try:
                # Normalizar datos
                normalized_data = normalize_json_data(json_record)
                date = normalized_data["date"]

                # Verificar si el registro ya existe
                from sqlmodel import select
                from src.bio.models import DailyBiometrics

                existing = session.exec(
                    select(DailyBiometrics).where(DailyBiometrics.date == date)
                ).first()

                # Insertar o actualizar usando el DAO (calcula métricas derivadas automáticamente)
                record = create_or_update_biometrics(
                    session=session,
                    data=normalized_data
                )

                if existing:
                    updated_count += 1
                    print(
                        f"  [{idx}/{len(data)}] Actualizado: {date} (ICD: {record.icd_score:.2f if record.icd_score else 'N/A'})")
                else:
                    inserted_count += 1
                    print(
                        f"  [{idx}/{len(data)}] Insertado: {date} (ICD: {record.icd_score:.2f if record.icd_score else 'N/A'})")

            except Exception as e:
                error_count += 1
                print(
                    f"  [{idx}/{len(data)}] ERROR procesando registro {json_record.get('date', 'desconocido')}: {e}")
                continue

    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN DE INGESTA")
    print("=" * 80)
    print(f"Total registros procesados: {len(data)}")
    print(f"  - Insertados: {inserted_count}")
    print(f"  - Actualizados: {updated_count}")
    print(f"  - Errores: {error_count}")
    print("=" * 80)


def main():
    """Función principal para ejecutar la ingesta desde línea de comandos."""
    # Ruta al archivo JSON (relativa al directorio raíz del proyecto)
    json_path = project_root / "data" / "biometrics" / "suunto_data.json"

    print("=" * 80)
    print("INGESTA DE DATOS SUUNTO DESDE JSON")
    print("=" * 80)
    print(f"Archivo JSON: {json_path}")
    print(f"Base de datos: {project_root / 'data' / 'metrics.db'}")
    print("=" * 80 + "\n")

    try:
        ingest_suunto_json(json_path=json_path)
        print("\n✅ Ingesta completada exitosamente")
    except Exception as e:
        print(f"\n❌ Error durante la ingesta: {e}")
        raise


if __name__ == "__main__":
    main()
