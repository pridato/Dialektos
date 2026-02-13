#!/usr/bin/env python3
"""
Script de Limpieza de Chunks Duplicados en ChromaDB

Lee el reporte generado por detect_duplicates.py y elimina los chunks
duplicados de forma segura, manteniendo solo el primer registro de cada grupo.

IMPORTANTE: Este script modifica la base de datos. Asegúrate de tener un backup.

Uso:
    python scripts/db/cleanup_duplicates.py
    
Prerrequisitos:
    - Ejecutar primero: python scripts/db/detect_duplicates.py
    - Hacer backup: cp -r data/chroma_db data/chroma_db.backup
    
Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import sys

# Importar ChromaDB para eliminar de forma segura
try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("❌ Error: chromadb no está instalado")
    print("   Instala con: pip install chromadb")
    sys.exit(1)


class DuplicateCleaner:
    """Limpiador de chunks duplicados en ChromaDB."""
    
    def __init__(self, chroma_dir: Path, report_path: Path):
        """
        Inicializa el limpiador.
        
        Args:
            chroma_dir: Directorio de ChromaDB
            report_path: Ruta al reporte de duplicados
        """
        self.chroma_dir = chroma_dir
        self.report_path = report_path
        self.report = None
        self.client = None
        self.collection = None
        
    def load_report(self) -> Dict:
        """
        Carga el reporte de duplicados.
        
        Returns:
            Diccionario con el reporte
            
        Raises:
            FileNotFoundError: Si el reporte no existe
        """
        if not self.report_path.exists():
            raise FileNotFoundError(
                f"Reporte no encontrado: {self.report_path}\n"
                "   Ejecuta primero: python scripts/db/detect_duplicates.py"
            )
        
        with open(self.report_path, 'r', encoding='utf-8') as f:
            self.report = json.load(f)
        
        print(f"✅ Reporte cargado: {self.report_path}")
        return self.report
    
    def create_backup(self) -> Path:
        """
        Crea un backup del directorio de ChromaDB.
        
        Returns:
            Ruta del backup creado
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.chroma_dir.parent / f"chroma_db_backup_{timestamp}"
        
        print(f"\n💾 Creando backup...")
        print(f"   Origen: {self.chroma_dir}")
        print(f"   Destino: {backup_dir}")
        
        shutil.copytree(self.chroma_dir, backup_dir)
        
        # Verificar tamaño del backup
        backup_size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
        backup_size_mb = backup_size / (1024 * 1024)
        
        print(f"✅ Backup creado ({backup_size_mb:.2f} MB)")
        
        return backup_dir
    
    def connect_to_chromadb(self) -> None:
        """Conecta a ChromaDB."""
        print(f"\n🔗 Conectando a ChromaDB...")
        
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Obtener la colección (asumimos que hay una sola)
        collections = self.client.list_collections()
        
        if not collections:
            raise ValueError("No se encontraron colecciones en ChromaDB")
        
        self.collection = collections[0]
        print(f"✅ Conectado a colección: {self.collection.name}")
        print(f"   Chunks actuales: {self.collection.count():,}")
    
    def delete_duplicates(self, dry_run: bool = False) -> Dict:
        """
        Elimina los chunks duplicados.
        
        Args:
            dry_run: Si es True, solo simula la eliminación sin hacer cambios
            
        Returns:
            Diccionario con estadísticas de la operación
        """
        if not self.report:
            raise ValueError("Reporte no cargado. Llama a load_report() primero.")
        
        duplicate_groups = self.report.get("duplicate_groups", [])
        total_to_remove = self.report["summary"]["total_ids_to_remove"]
        
        if total_to_remove == 0:
            print("\n✅ No hay duplicados para eliminar")
            return {"removed": 0, "errors": 0}
        
        print(f"\n🗑️  {'[DRY RUN] ' if dry_run else ''}Eliminando duplicados...")
        print(f"   Grupos de duplicados: {len(duplicate_groups)}")
        print(f"   Chunks a eliminar: {total_to_remove}")
        
        # Recopilar todos los IDs a eliminar
        ids_to_remove = []
        for group in duplicate_groups:
            ids_to_remove.extend(group["remove_ids"])
        
        print(f"\n   Total de IDs recopilados: {len(ids_to_remove)}")
        
        if dry_run:
            print("\n⚠️  DRY RUN: No se realizarán cambios reales")
            print(f"   Se eliminarían {len(ids_to_remove)} chunks")
            return {"removed": 0, "errors": 0, "would_remove": len(ids_to_remove)}
        
        # Eliminar en batches para eficiencia
        batch_size = 100
        removed_count = 0
        error_count = 0
        
        for i in range(0, len(ids_to_remove), batch_size):
            batch_ids = ids_to_remove[i:i + batch_size]
            
            try:
                self.collection.delete(ids=batch_ids)
                removed_count += len(batch_ids)
                
                # Actualizar progreso
                progress = (i + batch_size) / len(ids_to_remove) * 100
                print(f"   Progreso: {min(progress, 100):.1f}% ({removed_count}/{len(ids_to_remove)})", end='\r')
                
            except Exception as e:
                error_count += len(batch_ids)
                print(f"\n   ⚠️  Error al eliminar batch {i//batch_size + 1}: {e}")
        
        print(f"\n   Progreso: 100.0% ({removed_count}/{len(ids_to_remove)})    ")
        
        return {"removed": removed_count, "errors": error_count}
    
    def verify_cleanup(self) -> Dict:
        """
        Verifica el resultado de la limpieza.
        
        Returns:
            Diccionario con estadísticas post-limpieza
        """
        print(f"\n🔍 Verificando limpieza...")
        
        # Contar chunks restantes
        final_count = self.collection.count()
        expected_count = self.report["statistics"]["unique_chunks"] + self.report["statistics"]["duplicate_groups"]
        
        stats = {
            "final_count": final_count,
            "expected_count": expected_count,
            "matches_expected": final_count == expected_count
        }
        
        print(f"   Chunks finales: {final_count:,}")
        print(f"   Chunks esperados: {expected_count:,}")
        
        if stats["matches_expected"]:
            print(f"   ✅ La limpieza fue exitosa")
        else:
            diff = abs(final_count - expected_count)
            print(f"   ⚠️  Diferencia detectada: {diff} chunks")
        
        return stats
    
    def generate_cleanup_report(self, backup_path: Path, deletion_stats: Dict, 
                                 verification_stats: Dict) -> Dict:
        """
        Genera un reporte de la operación de limpieza.
        
        Args:
            backup_path: Ruta del backup creado
            deletion_stats: Estadísticas de eliminación
            verification_stats: Estadísticas de verificación
            
        Returns:
            Diccionario con el reporte completo
        """
        report = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "backup_location": str(backup_path),
                "chroma_directory": str(self.chroma_dir)
            },
            "original_stats": self.report["statistics"],
            "deletion_stats": deletion_stats,
            "verification_stats": verification_stats,
            "success": deletion_stats["errors"] == 0 and verification_stats["matches_expected"]
        }
        
        return report
    
    def save_cleanup_report(self, report: Dict, output_path: Path) -> None:
        """
        Guarda el reporte de limpieza.
        
        Args:
            report: Reporte a guardar
            output_path: Ruta del archivo de salida
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Reporte de limpieza guardado: {output_path}")
    
    def print_summary(self, deletion_stats: Dict, verification_stats: Dict) -> None:
        """
        Imprime un resumen de la operación.
        
        Args:
            deletion_stats: Estadísticas de eliminación
            verification_stats: Estadísticas de verificación
        """
        print("\n" + "=" * 80)
        print("📊 RESUMEN DE LIMPIEZA")
        print("=" * 80)
        print(f"Chunks originales:    {self.report['statistics']['total_chunks']:,}")
        print(f"Chunks eliminados:    {deletion_stats['removed']:,}")
        print(f"Chunks finales:       {verification_stats['final_count']:,}")
        print(f"Errores:              {deletion_stats['errors']}")
        
        if deletion_stats['errors'] == 0 and verification_stats['matches_expected']:
            print("\n✅ LIMPIEZA EXITOSA")
        else:
            print("\n⚠️  LIMPIEZA CON ADVERTENCIAS - Revisa el reporte detallado")
        
        print("=" * 80)


def confirm_action() -> bool:
    """
    Solicita confirmación del usuario antes de proceder.
    
    Returns:
        True si el usuario confirma, False en caso contrario
    """
    print("\n" + "=" * 80)
    print("⚠️  ADVERTENCIA: Esta operación modificará la base de datos")
    print("=" * 80)
    print("Se eliminará permanentemente el 75% de los chunks duplicados.")
    print("Se creará un backup automático antes de proceder.")
    print()
    
    response = input("¿Deseas continuar? (escribe 'SI' para confirmar): ").strip()
    
    return response.upper() == "SI"


def main():
    """Función principal."""
    print("=" * 80)
    print("🗑️  LIMPIEZA DE DUPLICADOS EN CHROMADB")
    print("=" * 80)
    
    # Configuración
    CHROMA_DIR = Path("data/chroma_db")
    REPORT_PATH = Path("scripts/db/duplicates_report.json")
    CLEANUP_REPORT_PATH = Path("scripts/db/cleanup_report.json")
    
    try:
        # Inicializar limpiador
        cleaner = DuplicateCleaner(CHROMA_DIR, REPORT_PATH)
        
        # Cargar reporte de duplicados
        cleaner.load_report()
        
        # Mostrar estadísticas
        stats = cleaner.report["statistics"]
        print(f"\n📊 Estadísticas del reporte:")
        print(f"   Total de chunks: {stats['total_chunks']:,}")
        print(f"   Chunks a eliminar: {stats['chunks_to_remove']:,}")
        print(f"   Tasa de duplicación: {stats['duplication_rate']:.1f}%")
        
        if stats['chunks_to_remove'] == 0:
            print("\n✅ No hay duplicados para eliminar")
            return
        
        # Solicitar confirmación
        if not confirm_action():
            print("\n❌ Operación cancelada por el usuario")
            return
        
        # Crear backup
        backup_path = cleaner.create_backup()
        
        # Conectar a ChromaDB
        cleaner.connect_to_chromadb()
        
        # Eliminar duplicados
        deletion_stats = cleaner.delete_duplicates(dry_run=False)
        
        # Verificar limpieza
        verification_stats = cleaner.verify_cleanup()
        
        # Generar reporte de limpieza
        cleanup_report = cleaner.generate_cleanup_report(
            backup_path, deletion_stats, verification_stats
        )
        
        # Guardar reporte
        cleaner.save_cleanup_report(cleanup_report, CLEANUP_REPORT_PATH)
        
        # Mostrar resumen
        cleaner.print_summary(deletion_stats, verification_stats)
        
        # Información del backup
        print("\n" + "=" * 80)
        print("📦 BACKUP")
        print("=" * 80)
        print(f"Ubicación: {backup_path}")
        print("Para restaurar (si necesario):")
        print(f"  rm -rf {CHROMA_DIR}")
        print(f"  cp -r {backup_path} {CHROMA_DIR}")
        print("=" * 80)
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        print("\n⚠️  Si algo salió mal, restaura el backup:")
        print(f"   Busca el backup más reciente en: {CHROMA_DIR.parent}/chroma_db_backup_*")


if __name__ == "__main__":
    main()
