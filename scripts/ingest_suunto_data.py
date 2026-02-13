#!/usr/bin/env python3
"""
Script de Ingesta de Datos Suunto desde JSON

Lee el archivo JSON y inserta todos los registros en la base de datos,
calculando automáticamente las métricas derivadas.

Uso:
    python -m scripts.ingest_suunto_data
    O desde el directorio raíz: python scripts/ingest_suunto_data.py
"""
from __future__ import annotations

import json
from datetime import date as date_type
from pathlib import Path

from sqlmodel import Session, select

from src.bio.dao import create_or_update_biometrics
from src.bio.db import get_engine


def parse_date(date_str: str) -> date_type:
    """Convierte string YYYY-MM-DD a objeto date."""
    year, month, day = map(int, date_str.split("-"))
    return date_type(year, month, day)


def main():
    """Función principal."""
    # Rutas
    project_root = Path(__file__).resolve().parent.parent
    json_path = project_root / "data" / "biometrics" / "suunto_data.json"
    db_path = project_root / "data" / "metrics.db"
    
    print("=" * 80)
    print("INGESTA DE DATOS SUUNTO DESDE JSON")
    print("=" * 80)
    print(f"Archivo JSON: {json_path}")
    print(f"Base de datos: {db_path}")
    print("=" * 80 + "\n")
    
    # Leer JSON
    if not json_path.exists():
        print(f"❌ ERROR: No se encuentra el archivo {json_path}")
        return
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        print("❌ ERROR: El JSON debe contener una lista de registros")
        return
    
    print(f"✓ Encontrados {len(data)} registros en el JSON\n")
    
    # Conectar a BD
    engine = get_engine()
    
    inserted_count = 0
    updated_count = 0
    error_count = 0
    
    with Session(engine) as session:
        for idx, json_record in enumerate(data, start=1):
            try:
                # Normalizar fecha
                if "date" not in json_record:
                    raise ValueError("Campo 'date' faltante")
                
                date_obj = parse_date(json_record["date"])
                
                # Preparar datos (solo campos que existen y no son None)
                normalized_data = {"date": date_obj}
                
                # Campos objetivos
                for field in [
                    "hrv_rmssd", "resting_hr", "avg_hr_sleep", "sleep_total_min",
                    "deep_sleep_min", "rem_sleep_min", "light_sleep_min", "awake_min",
                    "sleep_start_time", "sleep_quality", "body_resources", "training_load"
                ]:
                    if field in json_record and json_record[field] is not None:
                        normalized_data[field] = json_record[field]
                
                # Campos subjetivos
                for field in [
                    "energy_level", "mental_clarity", "mood", "motivation", "muscle_soreness"
                ]:
                    if field in json_record and json_record[field] is not None:
                        normalized_data[field] = json_record[field]
                
                # Verificar si existe
                existing = session.exec(
                    select(DailyBiometrics).where(DailyBiometrics.date == date_obj)
                ).first()
                
                # Insertar/actualizar usando DAO (calcula métricas automáticamente)
                record = create_or_update_biometrics(
                    session=session,
                    data=normalized_data
                )
                
                if existing:
                    updated_count += 1
                    status = "Actualizado"
                else:
                    inserted_count += 1
                    status = "Insertado"
                
                icd_str = f"{record.icd_score:.2f}" if record.icd_score else "N/A"
                print(f"  [{idx:2d}/{len(data)}] {status:10s} {date_obj} → ICD: {icd_str}")
                
            except Exception as e:
                error_count += 1
                date_str = json_record.get("date", "desconocido")
                print(f"  [{idx:2d}/{len(data)}] ❌ ERROR en {date_str}: {e}")
                session.rollback()
                continue
    
    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN DE INGESTA")
    print("=" * 80)
    print(f"Total procesados: {len(data)}")
    print(f"  ✓ Insertados:   {inserted_count}")
    print(f"  ↻ Actualizados: {updated_count}")
    print(f"  ❌ Errores:      {error_count}")
    print("=" * 80)
    
    if error_count == 0:
        print("\n✅ Ingesta completada exitosamente")
    else:
        print(f"\n⚠️  Completado con {error_count} error(es)")


if __name__ == "__main__":
    # Importar aquí para evitar problemas de importación circular
    from src.bio.models import DailyBiometrics
    main()
