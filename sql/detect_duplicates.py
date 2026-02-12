#!/usr/bin/env python3
"""
Script de Detección de Chunks Duplicados en ChromaDB

Analiza la base de datos ChromaDB para identificar chunks con contenido
idéntico y genera un reporte detallado con estadísticas y lista de IDs
duplicados para su posterior eliminación.

Uso:
    python sql/detect_duplicates.py
    
Salida:
    - Reporte en consola con estadísticas
    - Archivo JSON: sql/duplicates_report.json
    
Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict


class DuplicateDetector:
    """Detector de chunks duplicados en ChromaDB."""
    
    def __init__(self, db_path: Path):
        """
        Inicializa el detector.
        
        Args:
            db_path: Ruta al archivo chroma.sqlite3
        """
        self.db_path = db_path
        self.conn = None
        
    def connect(self) -> None:
        """Conecta a la base de datos SQLite."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Base de datos no encontrada: {self.db_path}")
        
        self.conn = sqlite3.connect(self.db_path)
        print(f"✅ Conectado a: {self.db_path}")
        
    def get_collection_info(self) -> Dict:
        """Obtiene información básica de la colección."""
        cursor = self.conn.cursor()
        
        # Total de embeddings
        cursor.execute("SELECT COUNT(*) FROM embeddings")
        total_chunks = cursor.fetchone()[0]
        
        # Nombre de la colección
        cursor.execute("SELECT name FROM collections LIMIT 1")
        result = cursor.fetchone()
        collection_name = result[0] if result else "unknown"
        
        return {
            "total_chunks": total_chunks,
            "collection_name": collection_name
        }
    
    def find_duplicates_by_content(self) -> Tuple[Dict[str, List[str]], Dict]:
        """
        Identifica duplicados basándose en el contenido textual.
        
        Returns:
            Tupla con:
            - Diccionario {hash_contenido: [lista_de_ids]}
            - Estadísticas de duplicación
        """
        cursor = self.conn.cursor()
        
        # Obtener todos los chunks con su contenido
        # Nota: El texto está en embedding_metadata con key='chroma:document'
        print("\n🔍 Analizando contenido de chunks...")
        cursor.execute("""
            SELECT e.embedding_id, m.string_value
            FROM embeddings e
            JOIN embedding_metadata m ON e.id = m.id
            WHERE m.key = 'chroma:document'
            ORDER BY e.embedding_id
        """)
        
        # Agrupar por hash del contenido
        content_to_ids = defaultdict(list)
        total_analyzed = 0
        
        for embedding_id, document in cursor.fetchall():
            # Generar hash del contenido (normalizado)
            normalized_content = document.strip().lower()
            content_hash = hashlib.sha256(normalized_content.encode()).hexdigest()
            content_to_ids[content_hash].append(embedding_id)
            total_analyzed += 1
            
            if total_analyzed % 100 == 0:
                print(f"   Analizados: {total_analyzed} chunks...", end='\r')
        
        print(f"   Analizados: {total_analyzed} chunks    ")
        
        # Filtrar solo los que tienen duplicados
        duplicates_map = {
            content_hash: ids 
            for content_hash, ids in content_to_ids.items() 
            if len(ids) > 1
        }
        
        # Calcular estadísticas
        unique_chunks = len([ids for ids in content_to_ids.values() if len(ids) == 1])
        duplicate_groups = len(duplicates_map)
        total_duplicate_chunks = sum(len(ids) for ids in duplicates_map.values())
        chunks_to_remove = total_duplicate_chunks - duplicate_groups  # Mantener 1 por grupo
        
        stats = {
            "total_chunks": total_analyzed,
            "unique_chunks": unique_chunks,
            "duplicate_groups": duplicate_groups,
            "total_duplicate_chunks": total_duplicate_chunks,
            "chunks_to_remove": chunks_to_remove,
            "duplication_rate": (chunks_to_remove / total_analyzed * 100) if total_analyzed > 0 else 0
        }
        
        return duplicates_map, stats
    
    def get_chunk_details(self, chunk_ids: List[str]) -> List[Dict]:
        """
        Obtiene detalles de chunks específicos.
        
        Args:
            chunk_ids: Lista de embedding_ids de chunks
            
        Returns:
            Lista de diccionarios con detalles de cada chunk
        """
        cursor = self.conn.cursor()
        
        placeholders = ','.join('?' * len(chunk_ids))
        query = f"""
            SELECT e.embedding_id, m.string_value
            FROM embeddings e
            JOIN embedding_metadata m ON e.id = m.id
            WHERE m.key = 'chroma:document'
            AND e.embedding_id IN ({placeholders})
        """
        
        cursor.execute(query, chunk_ids)
        
        details = []
        for embedding_id, document in cursor.fetchall():
            details.append({
                "chunk_id": embedding_id,
                "text_preview": document[:100] + "..." if len(document) > 100 else document,
                "text_length": len(document)
            })
        
        return details
    
    def generate_report(self, duplicates_map: Dict[str, List[str]], stats: Dict) -> Dict:
        """
        Genera un reporte completo de duplicados.
        
        Args:
            duplicates_map: Mapa de duplicados
            stats: Estadísticas de duplicación
            
        Returns:
            Diccionario con reporte completo
        """
        print("\n📊 Generando reporte detallado...")
        
        # Preparar lista de grupos duplicados con detalles
        duplicate_groups_details = []
        
        for idx, (content_hash, chunk_ids) in enumerate(duplicates_map.items(), 1):
            # Obtener detalles del primer chunk como muestra
            sample_details = self.get_chunk_details([chunk_ids[0]])
            
            group = {
                "group_id": idx,
                "content_hash": content_hash,
                "duplicate_count": len(chunk_ids),
                "chunk_ids": chunk_ids,
                "keep_id": chunk_ids[0],  # Mantener el primero (más antiguo)
                "remove_ids": chunk_ids[1:],  # Eliminar el resto
                "sample_text": sample_details[0]["text_preview"] if sample_details else "N/A"
            }
            
            duplicate_groups_details.append(group)
            
            if idx % 10 == 0:
                print(f"   Procesados: {idx}/{len(duplicates_map)} grupos...", end='\r')
        
        print(f"   Procesados: {len(duplicates_map)}/{len(duplicates_map)} grupos    ")
        
        # Compilar reporte completo
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "database_path": str(self.db_path),
                "analysis_type": "content_based_deduplication"
            },
            "statistics": stats,
            "duplicate_groups": duplicate_groups_details,
            "summary": {
                "total_ids_to_remove": sum(len(g["remove_ids"]) for g in duplicate_groups_details),
                "total_ids_to_keep": len(duplicate_groups_details),
                "space_savings_estimate": f"{stats['duplication_rate']:.1f}%"
            }
        }
        
        return report
    
    def save_report(self, report: Dict, output_path: Path) -> None:
        """
        Guarda el reporte en formato JSON.
        
        Args:
            report: Reporte generado
            output_path: Ruta del archivo de salida
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Reporte guardado en: {output_path}")
    
    def print_summary(self, stats: Dict) -> None:
        """
        Imprime un resumen de estadísticas en consola.
        
        Args:
            stats: Estadísticas de duplicación
        """
        print("\n" + "=" * 80)
        print("📊 RESUMEN DE DUPLICADOS")
        print("=" * 80)
        print(f"Total de chunks:           {stats['total_chunks']:,}")
        print(f"Chunks únicos:             {stats['unique_chunks']:,}")
        print(f"Grupos de duplicados:      {stats['duplicate_groups']:,}")
        print(f"Total de chunks duplicados: {stats['total_duplicate_chunks']:,}")
        print(f"Chunks a eliminar:         {stats['chunks_to_remove']:,}")
        print(f"Tasa de duplicación:       {stats['duplication_rate']:.1f}%")
        print("=" * 80)
        
        if stats['duplication_rate'] > 50:
            print("⚠️  ALERTA: Tasa de duplicación muy alta (>50%)")
        elif stats['duplication_rate'] > 25:
            print("⚠️  ADVERTENCIA: Tasa de duplicación moderada (>25%)")
        else:
            print("✅ Tasa de duplicación aceptable (<25%)")
    
    def close(self) -> None:
        """Cierra la conexión a la base de datos."""
        if self.conn:
            self.conn.close()
            print("\n✅ Conexión cerrada")


def main():
    """Función principal."""
    print("=" * 80)
    print("🔍 DETECCIÓN DE DUPLICADOS EN CHROMADB")
    print("=" * 80)
    
    # Configuración
    DB_PATH = Path("data/chroma_db/chroma.sqlite3")
    OUTPUT_PATH = Path("sql/duplicates_report.json")
    
    try:
        # Inicializar detector
        detector = DuplicateDetector(DB_PATH)
        detector.connect()
        
        # Obtener info de la colección
        collection_info = detector.get_collection_info()
        print(f"\n📚 Colección: {collection_info['collection_name']}")
        print(f"📦 Total de chunks: {collection_info['total_chunks']:,}")
        
        # Detectar duplicados
        duplicates_map, stats = detector.find_duplicates_by_content()
        
        # Generar reporte
        report = detector.generate_report(duplicates_map, stats)
        
        # Guardar reporte
        detector.save_report(report, OUTPUT_PATH)
        
        # Mostrar resumen
        detector.print_summary(stats)
        
        # Cerrar conexión
        detector.close()
        
        # Siguientes pasos
        if stats['chunks_to_remove'] > 0:
            print("\n" + "=" * 80)
            print("📋 SIGUIENTES PASOS")
            print("=" * 80)
            print("1. Revisar el reporte: sql/duplicates_report.json")
            print("2. Hacer backup: cp -r data/chroma_db data/chroma_db.backup")
            print("3. Ejecutar limpieza: python sql/cleanup_duplicates.py")
            print("=" * 80)
        else:
            print("\n✅ No se encontraron duplicados. La base de datos está limpia.")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("   Asegúrate de que la base de datos existe en data/chroma_db/")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
