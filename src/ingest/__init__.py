"""
Módulo de Ingesta de Datos (Data Pipeline)

Este módulo contiene las herramientas para extraer, limpiar y 
estructurar datos desde diferentes fuentes (PDFs, texto plano, etc.)
"""

from .pdf_extractor import PDFExtractor, ProcessedDocument, DocumentMetadata

__all__ = [
    'PDFExtractor',
    'ProcessedDocument',
    'DocumentMetadata'
]
