"""
Script de prueba para verificar el cálculo de métricas derivadas.

Carga datos del JSON de Suunto y verifica que las métricas derivadas
se calculan correctamente al insertar registros.

Uso:
    python -m src.bio.test_metrics
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlmodel import Session

from src.bio.dao import create_or_update_biometrics
from src.bio.db import get_engine, init_metrics_db
from src.bio.models import DailyBiometrics


def load_suunto_data(json_path: Path) -> list[dict]:
    """Carga datos del JSON de Suunto."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_metrics_calculation():
    """Prueba el cálculo de métricas derivadas."""
    # Inicializar base de datos
    print("Inicializando base de datos...")
    init_metrics_db()
    
    # Cargar datos de ejemplo
    json_path = Path(__file__).parent.parent.parent / "data" / "biometrics" / "suunto_data.json"
    print(f"Cargando datos desde: {json_path}")
    data = load_suunto_data(json_path)
    
    # Crear sesión
    engine = get_engine()
    
    print("\n" + "=" * 80)
    print("Insertando registros y calculando métricas derivadas...")
    print("=" * 80 + "\n")
    
    with Session(engine) as session:
        # Insertar los primeros 7 registros (para tener datos históricos suficientes)
        test_records = data[:7]
        
        for i, record_data in enumerate(test_records, 1):
            # Convertir fecha de string a date
            record_data["date"] = date.fromisoformat(record_data["date"])
            
            print(f"Registro {i}/{len(test_records)}: {record_data['date']}")
            
            # Insertar usando la función DAO que calcula métricas automáticamente
            record = create_or_update_biometrics(session=session, data=record_data)
            
            # Mostrar métricas calculadas
            print(f"  hrv_rmssd: {record.hrv_rmssd}")
            print(f"  ln_rmssd: {record.ln_rmssd}")
            print(f"  hrv_baseline_7d: {record.hrv_baseline_7d}")
            print(f"  sleep_start_time: {record.sleep_start_time}")
            print(f"  sleep_consistency: {record.sleep_consistency}")
            print()
    
    # Verificar resultados
    print("=" * 80)
    print("Verificando resultados...")
    print("=" * 80 + "\n")
    
    with Session(engine) as session:
        statement = select(DailyBiometrics).order_by(DailyBiometrics.date.asc())
        all_records = session.exec(statement).all()
        
        print(f"Total de registros insertados: {len(all_records)}\n")
        
        # Verificar que las métricas se calcularon
        records_with_ln_rmssd = [r for r in all_records if r.ln_rmssd is not None]
        records_with_baseline = [r for r in all_records if r.hrv_baseline_7d is not None]
        records_with_consistency = [r for r in all_records if r.sleep_consistency is not None]
        
        print(f"Registros con ln_rmssd calculado: {len(records_with_ln_rmssd)}/{len(all_records)}")
        print(f"Registros con hrv_baseline_7d calculado: {len(records_with_baseline)}/{len(all_records)}")
        print(f"Registros con sleep_consistency calculado: {len(records_with_consistency)}/{len(all_records)}")
        
        # Mostrar detalles de los últimos registros
        print("\nÚltimos 3 registros:")
        for record in all_records[-3:]:
            print(f"\n  Fecha: {record.date}")
            print(f"  HRV RMSSD: {record.hrv_rmssd}")
            print(f"  ln(RMSSD): {record.ln_rmssd}")
            print(f"  Baseline 7d: {record.hrv_baseline_7d}")
            print(f"  Sleep start: {record.sleep_start_time}")
            print(f"  Sleep consistency: {record.sleep_consistency}")
    
    print("\n" + "=" * 80)
    print("Prueba completada exitosamente!")
    print("=" * 80)


if __name__ == "__main__":
    from sqlmodel import select
    test_metrics_calculation()
