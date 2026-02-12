#!/usr/bin/env python3
"""
Script de Limpieza de Duplicados - ChromaDB Dialektos

Este script identifica y elimina chunks duplicados de la base de datos ChromaDB,
manteniendo solo la primera ocurrencia de cada chunk único.

IMPORTANTE: Hacer backup antes de ejecutar!

Autor: David Arroyo
Proyecto: Dialektos
"""

import sqlite3
from pathlib import Path
from datetime import datetime
import shutil
import sys


def backup_database(db_path: Path) -> Path:
    """Crear backup de la base de datos antes de modificarla."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"chroma_backup_{timestamp}.sqlite3"
    
    print(f"📦 Creando backup en: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print(f"✅ Backup completado: {backup_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    return backup_path


def analyze_duplicates(conn: sqlite3.Connection) -> dict:
    """Analizar duplicados en la base de datos."""
    cursor = conn.cursor()
    
    # Encontrar duplicados
    query = """
    SELECT 
        string_value as document_text,
        COUNT(*) as occurrences,
        MIN(id) as first_id,
        GROUP_CONCAT(id) as all_ids
    FROM embedding_metadata
    WHERE key = 'chroma:document'
    GROUP BY string_value
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC
    """
    
    cursor.execute(query)
    duplicates = cursor.fetchall()
    
    # Estadísticas
    total_query = """
    SELECT COUNT(*) 
    FROM embedding_metadata 
    WHERE key = 'chroma:document'
    """
    cursor.execute(total_query)
    total_chunks = cursor.fetchone()[0]
    
    unique_query = """
    SELECT COUNT(DISTINCT string_value) 
    FROM embedding_metadata 
    WHERE key = 'chroma:document'
    """
    cursor.execute(unique_query)
    unique_chunks = cursor.fetchone()[0]
    
    return {
        'total_chunks': total_chunks,
        'unique_chunks': unique_chunks,
        'duplicate_groups': len(duplicates),
        'duplicates': duplicates,
        'chunks_to_remove': total_chunks - unique_chunks
    }


def remove_duplicates(conn: sqlite3.Connection, dry_run: bool = True) -> dict:
    """
    Eliminar chunks duplicados manteniendo solo el primero.
    
    Args:
        conn: Conexión a la base de datos
        dry_run: Si es True, solo muestra qué se eliminaría sin hacerlo
    
    Returns:
        Diccionario con estadísticas de la operación
    """
    cursor = conn.cursor()
    
    # Identificar IDs a eliminar (todos excepto el primero de cada grupo)
    query = """
    WITH duplicate_groups AS (
        SELECT 
            string_value,
            id,
            ROW_NUMBER() OVER (PARTITION BY string_value ORDER BY id) as row_num
        FROM embedding_metadata
        WHERE key = 'chroma:document'
    )
    SELECT id
    FROM duplicate_groups
    WHERE row_num > 1
    """
    
    cursor.execute(query)
    ids_to_remove = [row[0] for row in cursor.fetchall()]
    
    if dry_run:
        print(f"\n🔍 MODO DRY-RUN (simulación)")
        print(f"   Se eliminarían {len(ids_to_remove)} registros duplicados")
        print(f"   Mostrando primeros 10 IDs:")
        for id in ids_to_remove[:10]:
            print(f"   - ID: {id}")
        if len(ids_to_remove) > 10:
            print(f"   ... y {len(ids_to_remove) - 10} más")
        return {'removed': 0, 'would_remove': len(ids_to_remove)}
    
    # Eliminar duplicados
    print(f"\n🗑️  Eliminando {len(ids_to_remove)} registros duplicados...")
    
    removed_count = 0
    for id in ids_to_remove:
        # Eliminar de embedding_metadata
        cursor.execute(
            "DELETE FROM embedding_metadata WHERE id = ?",
            (id,)
        )
        
        # Eliminar de embeddings
        cursor.execute(
            "DELETE FROM embeddings WHERE id = ?",
            (id,)
        )
        
        removed_count += 1
        
        if removed_count % 100 == 0:
            print(f"   Progreso: {removed_count}/{len(ids_to_remove)}")
    
    conn.commit()
    
    return {
        'removed': removed_count,
        'would_remove': 0
    }


def vacuum_database(conn: sqlite3.Connection):
    """Ejecutar VACUUM para recuperar espacio."""
    print("\n🧹 Optimizando base de datos (VACUUM)...")
    conn.execute("VACUUM")
    print("✅ Optimización completada")


def generate_cleanup_report(
    before: dict,
    after: dict,
    backup_path: Path,
    db_path: Path
) -> str:
    """Generar reporte de limpieza."""
    report = f"""
# 🧹 Reporte de Limpieza de Duplicados - ChromaDB

**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Base de datos**: {db_path}
**Backup**: {backup_path}

## Antes de la Limpieza
- Total de chunks: {before['total_chunks']:,}
- Chunks únicos: {before['unique_chunks']:,}
- Grupos de duplicados: {before['duplicate_groups']:,}
- Chunks a eliminar: {before['chunks_to_remove']:,}
- Porcentaje de duplicación: {(before['chunks_to_remove']/before['total_chunks']*100):.2f}%

## Después de la Limpieza
- Total de chunks: {after['total_chunks']:,}
- Chunks únicos: {after['unique_chunks']:,}
- Registros eliminados: {before['total_chunks'] - after['total_chunks']:,}
- Reducción: {((before['total_chunks'] - after['total_chunks'])/before['total_chunks']*100):.2f}%

## Tamaños de Archivo
- Tamaño antes: {backup_path.stat().st_size / 1024 / 1024:.2f} MB
- Tamaño después: {db_path.stat().st_size / 1024 / 1024:.2f} MB
- Espacio recuperado: {(backup_path.stat().st_size - db_path.stat().st_size) / 1024 / 1024:.2f} MB

## Estado
✅ Limpieza completada exitosamente

## Próximos Pasos
1. Verificar integridad de la BD
2. Re-ejecutar análisis de calidad
3. Probar búsquedas RAG

---
**Generado por**: cleanup_duplicates.py
"""
    return report


def main():
    """Función principal."""
    print("=" * 60)
    print("🧹 Script de Limpieza de Duplicados - ChromaDB Dialektos")
    print("=" * 60)
    
    # Configuración
    db_path = Path("data/chroma_db/chroma.sqlite3")
    reports_dir = Path("sql/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Verificar BD
    if not db_path.exists():
        print(f"❌ Error: Base de datos no encontrada en {db_path}")
        sys.exit(1)
    
    # Modo de ejecución
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("\n⚠️  MODO DRY-RUN (simulación)")
        print("   No se realizarán cambios en la base de datos")
        print("   Para ejecutar realmente, usa: python cleanup_duplicates.py --execute")
    else:
        print("\n⚠️  MODO EJECUCIÓN")
        print("   Se eliminarán duplicados permanentemente")
        response = input("   ¿Continuar? (sí/no): ")
        if response.lower() not in ['sí', 'si', 'yes', 's', 'y']:
            print("❌ Operación cancelada")
            sys.exit(0)
    
    # Conectar
    print(f"\n📊 Conectando a: {db_path}")
    conn = sqlite3.connect(db_path)
    
    try:
        # Analizar estado actual
        print("\n🔍 Analizando duplicados...")
        before = analyze_duplicates(conn)
        
        print(f"\n📈 Estado actual:")
        print(f"   Total de chunks: {before['total_chunks']:,}")
        print(f"   Chunks únicos: {before['unique_chunks']:,}")
        print(f"   Grupos de duplicados: {before['duplicate_groups']:,}")
        print(f"   Chunks duplicados: {before['chunks_to_remove']:,}")
        print(f"   Porcentaje duplicación: {(before['chunks_to_remove']/before['total_chunks']*100):.2f}%")
        
        # Crear backup si no es dry-run
        backup_path = None
        if not dry_run:
            conn.close()
            backup_path = backup_database(db_path)
            conn = sqlite3.connect(db_path)
        
        # Eliminar duplicados
        result = remove_duplicates(conn, dry_run=dry_run)
        
        if not dry_run:
            # Vacuum
            vacuum_database(conn)
            
            # Analizar después
            print("\n📊 Analizando estado final...")
            after = analyze_duplicates(conn)
            
            print(f"\n✅ Resultado:")
            print(f"   Registros eliminados: {result['removed']:,}")
            print(f"   Chunks finales: {after['total_chunks']:,}")
            print(f"   Reducción: {((before['total_chunks'] - after['total_chunks'])/before['total_chunks']*100):.2f}%")
            
            # Generar reporte
            report = generate_cleanup_report(before, after, backup_path, db_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = reports_dir / f"cleanup_report_{timestamp}.md"
            report_path.write_text(report, encoding='utf-8')
            
            print(f"\n📄 Reporte guardado en: {report_path}")
            print(f"💾 Backup guardado en: {backup_path}")
            print("\n✅ Limpieza completada exitosamente!")
        else:
            print(f"\n💡 Para ejecutar la limpieza real:")
            print(f"   python {Path(__file__).name} --execute")
    
    except Exception as e:
        print(f"\n❌ Error durante la limpieza: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
