"""
Módulo de Ingesta de Datos (Data Pipeline) - Arquitectura Modular

Este módulo contiene las herramientas para extraer, limpiar y 
estructurar datos desde diferentes fuentes (PDFs, texto plano, etc.)

Componentes principales:
    - models: Modelos Pydantic para datos estructurados
    - text_cleaner: Limpieza de texto con RegEx
    - pdf_reader: Extracción y chunking de PDFs
    - chroma_persistence: Persistencia optimizada en ChromaDB
    - pdf_extractor: Punto de entrada principal (backward compatibility)

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

# Importar desde los módulos especializados
from .models import DocumentMetadata, ProcessedDocument, DocumentChunk
from .text_cleaner import TextCleaner
from .pdf_reader import PDFExtractor
from .chroma_persistence import ChromaDBPersistence

# Exportar todos los componentes principales
__all__ = [
    # Modelos de datos
    'DocumentMetadata',
    'ProcessedDocument',
    'DocumentChunk',
    # Clases funcionales
    'TextCleaner',
    'PDFExtractor',
    'ChromaDBPersistence',
]
