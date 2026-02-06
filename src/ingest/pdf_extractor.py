"""
Script ETL: Extracción y Limpieza de Texto desde PDFs

Este módulo implementa un pipeline completo para convertir PDFs
(diseñados para impresoras) en texto estructurado y limpio (optimizado para máquinas).

Arquitectura del Pipeline:
    1. Extracción: Lee PDFs página por página
    2. Limpieza: Aplica RegEx para corregir artefactos del formato PDF
    3. Enriquecimiento: Añade metadatos (archivo, carpeta, página)
    4. Persistencia: Guarda objetos JSON con texto + contexto

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

from pypdf import PdfReader
from pydantic import BaseModel, Field, validator


# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pdf_extraction.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# ============================================================================
# MODELOS DE DATOS (Pydantic)
# ============================================================================

class DocumentMetadata(BaseModel):
    """
    Metadatos estructurados de un documento PDF.
    
    Attributes:
        filename: Nombre del archivo PDF (ej: "Tema1_Matrices.pdf")
        source_folder: Carpeta de origen relativa (ej: "Algebra")
        page_number: Número de página (1-indexed)
        total_pages: Total de páginas del documento
    """
    filename: str = Field(..., description="Nombre del archivo PDF")
    source_folder: str = Field(..., description="Carpeta de origen")
    page_number: int = Field(..., ge=1, description="Número de página")
    total_pages: int = Field(..., ge=1, description="Total de páginas")
    
    @validator('page_number')
    def validate_page_number(cls, v, values):
        """Valida que el número de página no exceda el total."""
        if 'total_pages' in values and v > values['total_pages']:
            raise ValueError(f"page_number ({v}) no puede ser mayor que total_pages ({values['total_pages']})")
        return v


class ProcessedDocument(BaseModel):
    """
    Documento procesado con texto limpio y metadatos.
    
    Attributes:
        text: Texto limpio y continuo (sin artefactos de PDF)
        metadata: Metadatos estructurados del documento
        char_count: Número de caracteres del texto limpio
        word_count: Número aproximado de palabras
    """
    text: str = Field(..., min_length=1, description="Texto procesado")
    metadata: DocumentMetadata
    char_count: int = Field(default=0, ge=0)
    word_count: int = Field(default=0, ge=0)
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-calcular métricas si no se proporcionan
        if self.char_count == 0:
            self.char_count = len(self.text)
        if self.word_count == 0:
            self.word_count = len(self.text.split())


# ============================================================================
# CLASE PRINCIPAL: PDFExtractor
# ============================================================================

class PDFExtractor:
    """
    Extractor y limpiador de texto desde archivos PDF.
    
    Este extractor aplica una serie de transformaciones RegEx para
    corregir los artefactos introducidos por el formato PDF:
    
    - Arregla palabras cortadas con guiones al final de línea
    - Normaliza saltos de línea (mantiene párrafos reales)
    - Elimina ruido (espacios múltiples, caracteres invisibles)
    
    Example:
        >>> extractor = PDFExtractor(input_folder="data/raw_pdfs")
        >>> documents = extractor.process_all_pdfs()
        >>> extractor.save_to_json(documents, "data/processed/texts.json")
    """
    
    def __init__(self, input_folder: Path | str):
        """
        Inicializa el extractor.
        
        Args:
            input_folder: Carpeta raíz que contiene los PDFs a procesar
        """
        self.input_folder = Path(input_folder)
        
        if not self.input_folder.exists():
            raise FileNotFoundError(f"La carpeta {self.input_folder} no existe")
        
        logger.info(f"PDFExtractor inicializado. Carpeta de entrada: {self.input_folder}")
    
    
    # ========================================================================
    # MÉTODOS DE LIMPIEZA (Data Cleaning)
    # ========================================================================
    
    @staticmethod
    def fix_hyphenation(text: str) -> str:
        """
        A. Arregla palabras cortadas con guiones al final de línea.
        
        Problema:
            En un PDF, si "Algoritmo" no cabe en una línea:
            "Algo-\nritmo" → La IA lee dos palabras sin sentido
        
        Solución:
            Detecta el patrón [Guion] + [Salto de Línea] y lo elimina
        
        Args:
            text: Texto con posibles guiones de separación
            
        Returns:
            Texto con palabras unidas correctamente
            
        Example:
            >>> PDFExtractor.fix_hyphenation("Algo-\nritmo")
            'Algoritmo'
        """
        # Patrón: guion seguido de salto de línea (puede haber espacios)
        pattern = r'-\s*\n\s*'
        cleaned = re.sub(pattern, '', text)
        
        logger.debug(f"Hyphenation fix: {text.count(pattern)} correcciones aplicadas")
        return cleaned
    
    
    @staticmethod
    def normalize_line_breaks(text: str) -> str:
        """
        B. Normaliza saltos de línea respetando párrafos reales.
        
        Problema:
            Los PDFs ponen '\n' al final de cada línea visual.
            Para una máquina, eso parece el fin de una frase.
        
        Solución:
            - Saltos de línea simples (\n) → espacio en blanco
            - Saltos de línea dobles (\n\n) → mantener (indican cambio de párrafo)
        
        Args:
            text: Texto con saltos de línea arbitrarios
            
        Returns:
            Texto con frases continuas y párrafos preservados
        """
        # Primero, proteger los saltos dobles (párrafos reales)
        text = re.sub(r'\n\n+', '<<PARAGRAPH>>', text)
        
        # Reemplazar saltos simples por espacios
        text = re.sub(r'\n', ' ', text)
        
        # Restaurar los párrafos reales
        text = re.sub(r'<<PARAGRAPH>>', '\n\n', text)
        
        return text
    
    
    @staticmethod
    def remove_noise(text: str) -> str:
        """
        C. Elimina ruido: espacios múltiples, tabulaciones, caracteres invisibles.
        
        Problema:
            Dobles espacios, tabs, caracteres de control residuales.
        
        Solución:
            Colapsar cualquier secuencia de espacios en blanco en un solo espacio.
        
        Args:
            text: Texto con posible ruido
            
        Returns:
            Texto con espaciado normalizado
        """
        # Reemplazar múltiples espacios (incluyendo tabs) por un solo espacio
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Eliminar espacios al inicio y final de cada línea
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Eliminar más de dos saltos de línea consecutivos
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    
    def clean_text(self, raw_text: str) -> str:
        """
        Pipeline completo de limpieza de texto.
        
        Aplica las tres etapas de limpieza en orden:
            1. Arreglar guiones (hyphenation)
            2. Normalizar saltos de línea
            3. Eliminar ruido
        
        Args:
            raw_text: Texto extraído directamente del PDF
            
        Returns:
            Texto limpio y continuo, listo para procesamiento NLP
        """
        logger.debug("Iniciando pipeline de limpieza")
        
        # Etapa A: Hyphenation
        text = self.fix_hyphenation(raw_text)
        
        # Etapa B: Line Breaks
        text = self.normalize_line_breaks(text)
        
        # Etapa C: Noise Reduction
        text = self.remove_noise(text)
        
        logger.debug(f"Limpieza completada. Longitud final: {len(text)} caracteres")
        return text
    
    
    # ========================================================================
    # MÉTODOS DE EXTRACCIÓN
    # ========================================================================
    
    def extract_from_pdf(self, pdf_path: Path) -> List[ProcessedDocument]:
        """
        Extrae texto de un PDF página por página con metadatos.
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            Lista de documentos procesados (uno por página)
            
        Raises:
            Exception: Si hay error al leer el PDF
        """
        documents: List[ProcessedDocument] = []
        
        try:
            reader = PdfReader(str(pdf_path))
            total_pages = len(reader.pages)
            
            # Calcular carpeta relativa (para metadatos)
            relative_folder = pdf_path.parent.relative_to(self.input_folder)
            source_folder = str(relative_folder) if str(relative_folder) != '.' else 'root'
            
            logger.info(f"Procesando: {pdf_path.name} ({total_pages} páginas)")
            
            for page_num, page in enumerate(reader.pages, start=1):
                # Extraer texto crudo
                raw_text = page.extract_text()
                
                if not raw_text or len(raw_text.strip()) == 0:
                    logger.warning(f"Página {page_num} de {pdf_path.name} está vacía. Saltando.")
                    continue
                
                # Limpiar texto
                clean_text = self.clean_text(raw_text)
                
                # Crear objeto con metadatos
                doc = ProcessedDocument(
                    text=clean_text,
                    metadata=DocumentMetadata(
                        filename=pdf_path.name,
                        source_folder=source_folder,
                        page_number=page_num,
                        total_pages=total_pages
                    )
                )
                
                documents.append(doc)
                logger.debug(f"✓ Página {page_num}/{total_pages} procesada ({doc.char_count} chars)")
            
            logger.info(f"✓ {pdf_path.name} completado: {len(documents)} páginas extraídas")
            return documents
        
        except Exception as e:
            logger.error(f"✗ Error procesando {pdf_path.name}: {str(e)}")
            raise
    
    
    def process_all_pdfs(self) -> List[ProcessedDocument]:
        """
        Procesa todos los PDFs encontrados en la carpeta de entrada (recursivamente).
        
        Returns:
            Lista completa de documentos procesados de todos los PDFs
        """
        all_documents: List[ProcessedDocument] = []
        
        # Buscar todos los PDFs (recursivamente)
        pdf_files = list(self.input_folder.rglob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No se encontraron archivos PDF en {self.input_folder}")
            return all_documents
        
        logger.info(f"🚀 Iniciando procesamiento de {len(pdf_files)} archivos PDF")
        
        for pdf_path in pdf_files:
            try:
                docs = self.extract_from_pdf(pdf_path)
                all_documents.extend(docs)
            except Exception as e:
                logger.error(f"Saltando {pdf_path.name} debido a error: {e}")
                continue
        
        logger.info(f"✅ Procesamiento completado: {len(all_documents)} páginas extraídas en total")
        return all_documents
    
    
    # ========================================================================
    # MÉTODOS DE PERSISTENCIA
    # ========================================================================
    
    @staticmethod
    def save_to_json(documents: List[ProcessedDocument], output_path: Path | str) -> None:
        """
        Guarda los documentos procesados en formato JSON.
        
        Args:
            documents: Lista de documentos procesados
            output_path: Ruta del archivo JSON de salida
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convertir a diccionarios serializables
        data = [doc.dict() for doc in documents]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Documentos guardados en: {output_path}")
        logger.info(f"   - Total documentos: {len(documents)}")
        logger.info(f"   - Tamaño del archivo: {output_path.stat().st_size / 1024:.2f} KB")


# ============================================================================
# FUNCIÓN PRINCIPAL (CLI)
# ============================================================================

def main():
    """
    Función principal para ejecutar el ETL desde línea de comandos.
    
    Usage:
        python pdf_extractor.py
    """
    logger.info("=" * 80)
    logger.info("ETL - EXTRACCIÓN DE TEXTO DESDE PDFs")
    logger.info("=" * 80)
    
    # Configuración
    INPUT_FOLDER = Path("data/raw_pdfs")
    OUTPUT_FILE = Path("data/processed/extracted_texts.json")
    
    # Ejecutar pipeline
    extractor = PDFExtractor(input_folder=INPUT_FOLDER)
    documents = extractor.process_all_pdfs()
    
    if documents:
        extractor.save_to_json(documents, output_path=OUTPUT_FILE)
        
        # Estadísticas finales
        total_chars = sum(doc.char_count for doc in documents)
        total_words = sum(doc.word_count for doc in documents)
        
        logger.info("\n" + "=" * 80)
        logger.info("ESTADÍSTICAS FINALES")
        logger.info("=" * 80)
        logger.info(f"📄 Páginas procesadas: {len(documents)}")
        logger.info(f"📝 Total caracteres: {total_chars:,}")
        logger.info(f"📖 Total palabras: {total_words:,}")
        logger.info(f"💾 Archivo generado: {OUTPUT_FILE}")
    else:
        logger.warning("No se procesaron documentos. Verifica la carpeta de entrada.")


if __name__ == "__main__":
    main()
