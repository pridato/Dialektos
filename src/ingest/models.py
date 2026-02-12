"""
Modelos de Datos Pydantic - Sistema RAG Dialektos

Este módulo define los modelos de datos utilizados en el pipeline ETL
para extraer, limpiar y estructurar documentos PDF.

Modelos:
    - DocumentMetadata: Metadatos básicos de un documento PDF
    - StructuredMetadata: Metadatos enriquecidos para filtrado avanzado
    - ProcessedDocument: Documento procesado con texto limpio
    - DocumentChunk: Fragmento de texto optimizado para embeddings

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import hashlib
from typing import Optional

from pydantic import BaseModel, Field, SerializeAsAny, validator


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


class StructuredMetadata(DocumentMetadata):
    """
    Metadatos enriquecidos para filtrado avanzado en el sistema RAG.
    
    Hereda de DocumentMetadata para backward compatibility total:
    cualquier código que espere DocumentMetadata seguirá funcionando
    con instancias de StructuredMetadata sin cambios.
    
    Los campos nuevos son opcionales (Optional[str]) para que el pipeline
    no rompa si falta algún metadato — se irán poblando progresivamente
    mediante inferencia automática y/o configuración manual.
    
    Attributes:
        asignatura: Materia académica (ej: "Cálculo", "Álgebra Lineal")
        tipo: Categoría del material (ej: "Teoría", "Ejercicios", "Exámenes")
        fecha: Año o fecha del material (ej: "2024")
        idioma: Código de idioma ISO 639-1 (ej: "es", "en")
        autor: Autor del documento
        nivel_dificultad: Nivel estimado (ej: "basico", "intermedio", "avanzado")
        tema_especifico: Tema concreto dentro de la asignatura (ej: "Matrices")
    """
    asignatura: Optional[str] = Field(
        None, description="Materia académica (ej: Cálculo, Álgebra Lineal)"
    )
    tipo: Optional[str] = Field(
        None, description="Categoría del material (ej: Teoría, Ejercicios, Exámenes, Referencia)"
    )
    fecha: Optional[str] = Field(
        None, description="Año o fecha del material (ej: 2024)"
    )
    idioma: Optional[str] = Field(
        None, description="Código de idioma ISO 639-1 (ej: es, en, fr)"
    )
    autor: Optional[str] = Field(
        None, description="Autor del documento"
    )
    nivel_dificultad: Optional[str] = Field(
        None, description="Nivel estimado (ej: basico, intermedio, avanzado)"
    )
    tema_especifico: Optional[str] = Field(
        None, description="Tema concreto dentro de la asignatura (ej: Matrices, Integrales)"
    )


class ProcessedDocument(BaseModel):
    """
    Documento procesado con texto limpio y metadatos.
    
    Attributes:
        text: Texto limpio y continuo (sin artefactos de PDF)
        metadata: Metadatos estructurados del documento (DocumentMetadata o StructuredMetadata)
        char_count: Número de caracteres del texto limpio
        word_count: Número aproximado de palabras
    """
    text: str = Field(..., min_length=1, description="Texto procesado")
    metadata: SerializeAsAny[DocumentMetadata]
    char_count: int = Field(default=0, ge=0)
    word_count: int = Field(default=0, ge=0)
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-calcular métricas si no se proporcionan
        if self.char_count == 0:
            self.char_count = len(self.text)
        if self.word_count == 0:
            self.word_count = len(self.text.split())


class DocumentChunk(BaseModel):
    """
    Fragmento de texto optimizado para embeddings.
    
    Un chunk es una porción semántica de un documento original que:
    - No corta frases a la mitad (respeta separadores naturales)
    - Tiene un tamaño óptimo para modelos de embeddings (~1000 tokens)
    - Mantiene contexto mediante solapamiento con chunks adyacentes
    
    IMPORTANTE: El chunk_id se genera automáticamente usando un hash SHA-256
    del contenido textual. Esto garantiza que:
    - Mismo texto = Mismo ID (determinista)
    - Ejecuciones múltiples no crean duplicados
    - Es idempotente y predecible
    
    Attributes:
        chunk_id: ID único generado automáticamente del hash del texto
        text: Texto del fragmento (limpio y continuo)
        chunk_index: Posición del chunk dentro del documento (0-indexed)
        total_chunks: Total de chunks generados del documento original
        metadata: Metadatos heredados del documento original
        char_count: Número de caracteres del chunk
        token_count: Número aproximado de tokens (4 chars ≈ 1 token)
    """
    chunk_id: str = Field(default="", description="ID único del chunk (generado automáticamente)")
    text: str = Field(..., min_length=10, description="Texto del chunk")
    chunk_index: int = Field(..., ge=0, description="Índice del chunk")
    total_chunks: int = Field(..., ge=1, description="Total de chunks del documento")
    metadata: SerializeAsAny[DocumentMetadata]
    char_count: int = Field(default=0, ge=0)
    token_count: int = Field(default=0, ge=0)
    
    def __init__(self, **data):
        # Generar chunk_id si no se proporciona
        if not data.get('chunk_id'):
            text = data.get('text', '')
            # Hash SOLO del contenido textual (sin metadata) para idempotencia
            # Normalizamos el texto para evitar variaciones por espacios
            normalized_text = text.strip()
            content_hash = hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
            # Usar primeros 16 caracteres para IDs más cortos pero únicos
            data['chunk_id'] = content_hash[:16]
        
        super().__init__(**data)
        
        # Auto-calcular métricas si no se proporcionan
        if self.char_count == 0:
            self.char_count = len(self.text)
        if self.token_count == 0:
            self.token_count = len(self.text) // 4  # Aproximación: 4 chars ≈ 1 token
    
    @validator('chunk_index')
    def validate_chunk_index(cls, v, values):
        """Valida que el índice del chunk no exceda el total."""
        if 'total_chunks' in values and v >= values['total_chunks']:
            raise ValueError(f"chunk_index ({v}) debe ser menor que total_chunks ({values['total_chunks']})")
        return v
