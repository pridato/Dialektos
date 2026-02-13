#!/usr/bin/env python3
"""
Script simple de ingesta de datos Suunto desde JSON

Uso:
    python scripts/ingest_json_simple.py
"""
from src.bio.metrics import compute_derived_metrics
from src.bio.models import DailyBiometrics
from src.bio.db import get_engine
from sqlmodel import Session, select
import json
import sys
from datetime import date
from pathlib import Path

# Añadir el directorio raíz al path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def main():
    # Ruta al JSON
    json_path = project_root / "data" / "biometrics" / "suunto_data.json"

    print("=" * 80)
    print("INGESTA DE DATOS SUUNTO DESDE JSON")
    print("=" * 80)
    print(f"Archivo: {json_path}")
    print("=" * 80 + "\n")

    # Leer JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Encontrados {len(data)} registros\n")

    # Conectar a BD
    engine = get_engine()

    inserted = 0
    updated = 0

    with Session(engine) as session:
        for idx, record_data in enumerate(data, 1):
            try:
                # Convertir fecha
                date_obj = date(*map(int, record_data["date"].split("-")))

                # Buscar registro existente
                existing = session.exec(
                    select(DailyBiometrics).where(
                        DailyBiometrics.date == date_obj)
                ).first()

                # Preparar datos
                db_data = {}
                for key, value in record_data.items():
                    if key == "date":
                        db_data[key] = date_obj
                    elif value is not None:
                        db_data[key] = value

                # Crear o actualizar
                if existing:
                    for k, v in db_data.items():
                        if hasattr(existing, k):
                            setattr(existing, k, v)
                    record = existing
                    updated += 1
                    action = "Actualizado"
                else:
                    record = DailyBiometrics(**db_data)
                    session.add(record)
                    inserted += 1
                    action = "Insertado"

                # Calcular métricas derivadas
                record = compute_derived_metrics(session, record)

                # Guardar
                session.commit()
                session.refresh(record)

                icd_str = f"{record.icd_score:.2f}" if record.icd_score else "N/A"
                print(
                    f"  [{idx}/{len(data)}] {action}: {date_obj} (ICD: {icd_str})")

            except Exception as e:
                print(f"  [{idx}/{len(data)}] ERROR: {e}")
                session.rollback()
                continue

    print("\n" + "=" * 80)
    print(f"Insertados: {inserted}, Actualizados: {updated}")
    print("=" * 80)


if __name__ == "__main__":
    main()
