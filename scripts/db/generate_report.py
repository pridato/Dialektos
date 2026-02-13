#!/usr/bin/env python3
"""
Generador de Reportes ChromaDB - Sistema RAG Dialektos

Este script genera un reporte detallado en formato Markdown con análisis
completo de la base de datos ChromaDB, incluyendo gráficos y estadísticas.

Autor: David Arroyo
Proyecto: Dialektos
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
import sys


class ChromaDBReporter:
    """Generador de reportes para análisis de ChromaDB."""
    
    def __init__(self, db_path: str = "data/chroma_db/chroma.sqlite3"):
        self.db_path = Path(db_path)
        self.conn = None
        self.report_lines: List[str] = []
        
    def connect(self) -> bool:
        """Conectar a la base de datos."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            return True
        except Exception as e:
            print(f"❌ Error al conectar: {e}")
            return False
    
    def query(self, sql: str) -> List[Tuple]:
        """Ejecutar consulta SQL."""
        cursor = self.conn.cursor()
        cursor.execute(sql)
        return cursor.fetchall()
    
    def add_header(self, title: str, level: int = 1):
        """Agregar encabezado al reporte."""
        prefix = "#" * level
        self.report_lines.append(f"\n{prefix} {title}\n")
    
    def add_text(self, text: str):
        """Agregar texto al reporte."""
        self.report_lines.append(f"{text}\n")
    
    def add_table(self, headers: List[str], rows: List[Tuple]):
        """Agregar tabla Markdown al reporte."""
        if not rows:
            self.add_text("_No hay datos disponibles_")
            return
        
        # Encabezados
        header_line = "| " + " | ".join(str(h) for h in headers) + " |"
        separator = "|" + "|".join("---" for _ in headers) + "|"
        self.report_lines.append(header_line)
        self.report_lines.append(separator)
        
        # Filas
        for row in rows:
            row_line = "| " + " | ".join(str(cell) for cell in row) + " |"
            self.report_lines.append(row_line)
        
        self.report_lines.append("")
    
    def generate_schema_section(self):
        """Generar sección de esquema."""
        self.add_header("🗂️ Esquema de la Base de Datos", 2)
        
        # Tablas
        tables = self.query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        self.add_text(f"**Total de tablas:** {len(tables)}")
        self.add_table(["Tabla"], tables)
    
    def generate_collection_section(self):
        """Generar sección de colecciones."""
        self.add_header("📚 Colecciones", 2)
        
        collections = self.query("""
            SELECT name, id, dimension, topic 
            FROM collections
        """)
        
        if collections:
            self.add_table(
                ["Nombre", "ID", "Dimensiones", "Tema"],
                collections
            )
            
            # Documentos por colección
            for coll_name, coll_id, _, _ in collections:
                count = self.query(f"""
                    SELECT COUNT(*) 
                    FROM embeddings 
                    WHERE collection_id = '{coll_id}'
                """)[0][0]
                self.add_text(f"- **{coll_name}**: {count:,} embeddings")
    
    def generate_chunks_section(self):
        """Generar sección de análisis de chunks."""
        self.add_header("📝 Análisis de Chunks", 2)
        
        # Estadísticas generales
        stats = self.query("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT document) as unique_docs,
                MIN(LENGTH(document)) as min_len,
                MAX(LENGTH(document)) as max_len,
                AVG(LENGTH(document)) as avg_len,
                COUNT(DISTINCT metadata) as unique_metadata
            FROM embeddings
        """)[0]
        
        self.add_text(f"**Estadísticas Generales:**")
        self.add_table(
            ["Métrica", "Valor"],
            [
                ("Total de chunks", f"{stats[0]:,}"),
                ("Documentos únicos", f"{stats[1]:,}"),
                ("Longitud mínima", f"{stats[2]} chars"),
                ("Longitud máxima", f"{stats[3]} chars"),
                ("Longitud promedio", f"{stats[4]:.2f} chars"),
                ("Metadatos únicos", f"{stats[5]:,}"),
            ]
        )
        
        # Distribución por longitud
        self.add_header("Distribución por Longitud", 3)
        distribution = self.query("""
            SELECT 
                CASE 
                    WHEN LENGTH(document) < 100 THEN '0-100'
                    WHEN LENGTH(document) < 300 THEN '100-300'
                    WHEN LENGTH(document) < 500 THEN '300-500'
                    WHEN LENGTH(document) < 1000 THEN '500-1000'
                    ELSE '1000+'
                END as range,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM embeddings), 2) as percentage
            FROM embeddings
            GROUP BY range
            ORDER BY MIN(LENGTH(document))
        """)
        
        self.add_table(
            ["Rango (caracteres)", "Cantidad", "Porcentaje"],
            [(r, c, f"{p}%") for r, c, p in distribution]
        )
    
    def generate_quality_section(self):
        """Generar sección de calidad."""
        self.add_header("✅ Calidad de Datos", 2)
        
        # Completitud
        completeness = self.query("""
            SELECT 
                COUNT(*) as total,
                COUNT(embedding) as with_embedding,
                COUNT(document) as with_document,
                COUNT(metadata) as with_metadata
            FROM embeddings
        """)[0]
        
        total = completeness[0]
        self.add_table(
            ["Aspecto", "Cantidad", "Porcentaje"],
            [
                ("Con embedding", completeness[1], f"{completeness[1]/total*100:.2f}%"),
                ("Con documento", completeness[2], f"{completeness[2]/total*100:.2f}%"),
                ("Con metadata", completeness[3], f"{completeness[3]/total*100:.2f}%"),
            ]
        )
        
        # Problemas potenciales
        self.add_header("Problemas Potenciales", 3)
        problems = self.query("""
            SELECT 
                'Chunks vacíos' as problem,
                COUNT(*) as count
            FROM embeddings
            WHERE document IS NULL OR document = '' OR LENGTH(TRIM(document)) = 0
            
            UNION ALL
            
            SELECT 
                'Chunks muy cortos (<50 chars)',
                COUNT(*)
            FROM embeddings
            WHERE LENGTH(document) < 50
            
            UNION ALL
            
            SELECT 
                'Chunks muy largos (>2000 chars)',
                COUNT(*)
            FROM embeddings
            WHERE LENGTH(document) > 2000
        """)
        
        self.add_table(["Problema", "Cantidad"], problems)
        
        # Duplicación
        duplication = self.query("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT document) as unique,
                COUNT(*) - COUNT(DISTINCT document) as duplicates,
                ROUND((COUNT(*) - COUNT(DISTINCT document)) * 100.0 / COUNT(*), 2) as dup_percentage
            FROM embeddings
        """)[0]
        
        self.add_text(f"\n**Duplicación:**")
        self.add_text(f"- Total: {duplication[0]:,}")
        self.add_text(f"- Únicos: {duplication[1]:,}")
        self.add_text(f"- Duplicados: {duplication[2]:,} ({duplication[3]}%)")
        
        # Semáforo de calidad
        self.add_header("Semáforo de Calidad", 3)
        issues = []
        
        if duplication[3] > 10:
            issues.append("🔴 Alta duplicación (>10%)")
        elif duplication[3] > 5:
            issues.append("🟡 Duplicación moderada (5-10%)")
        else:
            issues.append("🟢 Duplicación baja (<5%)")
        
        if completeness[1]/total < 1.0:
            issues.append("🔴 Embeddings incompletos")
        else:
            issues.append("🟢 Embeddings completos")
        
        # Chunks problemáticos
        problem_count = sum(p[1] for p in problems)
        if problem_count > total * 0.05:
            issues.append("🔴 Más del 5% de chunks con problemas")
        elif problem_count > 0:
            issues.append("🟡 Algunos chunks con problemas")
        else:
            issues.append("🟢 Sin chunks problemáticos")
        
        for issue in issues:
            self.add_text(f"- {issue}")
    
    def generate_samples_section(self):
        """Generar sección de muestras."""
        self.add_header("🔍 Muestras de Chunks", 2)
        
        samples = self.query("""
            SELECT 
                id,
                SUBSTR(document, 1, 100) || '...' as preview,
                LENGTH(document) as length
            FROM embeddings
            ORDER BY RANDOM()
            LIMIT 5
        """)
        
        self.add_table(
            ["ID", "Preview", "Longitud"],
            samples
        )
    
    def generate_report(self) -> str:
        """Generar reporte completo."""
        if not self.connect():
            return "❌ No se pudo generar el reporte"
        
        # Encabezado principal
        self.add_header("📊 Reporte de Análisis ChromaDB - Dialektos")
        self.add_text(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.add_text(f"**Base de datos:** `{self.db_path}`")
        self.add_text(f"**Tamaño:** {self.db_path.stat().st_size / 1024 / 1024:.2f} MB")
        self.add_text("---")
        
        # Secciones
        try:
            self.generate_schema_section()
            self.generate_collection_section()
            self.generate_chunks_section()
            self.generate_quality_section()
            self.generate_samples_section()
        except Exception as e:
            self.add_text(f"\n⚠️ Error al generar sección: {e}")
        finally:
            if self.conn:
                self.conn.close()
        
        return "\n".join(self.report_lines)
    
    def save_report(self, output_path: str):
        """Guardar reporte en archivo."""
        report = self.generate_report()
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(report, encoding='utf-8')
        return output_file


def main():
    """Función principal."""
    print("🚀 Generando reporte de ChromaDB...")
    
    # Configuración
    db_path = "data/chroma_db/chroma.sqlite3"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"scripts/db/reports/analysis_{timestamp}.md"
    
    # Verificar que existe la BD
    if not Path(db_path).exists():
        print(f"❌ Error: No se encontró la base de datos en {db_path}")
        sys.exit(1)
    
    # Generar reporte
    reporter = ChromaDBReporter(db_path)
    report_file = reporter.save_report(output_path)
    
    print(f"✅ Reporte generado exitosamente")
    print(f"📄 Archivo: {report_file}")
    print(f"\n💡 Ver reporte:")
    print(f"   cat {report_file}")
    print(f"   # o")
    print(f"   open {report_file}  # (macOS)")


if __name__ == "__main__":
    main()
