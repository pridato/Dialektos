"""
Extracción de PDFs - Sistema RAG Dialektos

Este módulo implementa la extracción y chunking de texto desde archivos PDF.

Clase:
    PDFExtractor: Extrae texto de PDFs y lo divide en chunks semánticos

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Union

from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from .models import DocumentMetadata, ProcessedDocument, DocumentChunk, StructuredMetadata
from .metadata_extractor import MetadataExtractor
from .text_cleaner import TextCleaner


logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    Extractor y procesador de texto desde archivos PDF.
    
    Este extractor utiliza TextCleaner para limpiar el texto extraído
    y RecursiveCharacterTextSplitter para dividirlo en chunks semánticos.
    
    Example:
        >>> extractor = PDFExtractor(input_folder="data/raw_pdfs")
        >>> documents = extractor.process_all_pdfs()
        >>> extractor.save_to_json(documents, "data/processed/texts.json")
    """
    
    def __init__(
        self,
        input_folder: Path | str,
        metadata_extractor: Optional[MetadataExtractor] = None,
    ):
        """
        Inicializa el extractor.
        
        Args:
            input_folder: Carpeta raíz que contiene los PDFs a procesar
            metadata_extractor: Extractor de metadatos estructurados.
                                Si es None, se crea uno con la config por defecto.
        """
        self.input_folder = Path(input_folder)
        self.text_cleaner = TextCleaner()
        self.metadata_extractor = metadata_extractor or MetadataExtractor()
        
        if not self.input_folder.exists():
            raise FileNotFoundError(f"La carpeta {self.input_folder} no existe")
        
        logger.info(f"PDFExtractor inicializado. Carpeta de entrada: {self.input_folder}")
    
    
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
            
            # Recoger muestra de texto de las primeras páginas para detección de idioma
            text_sample_parts: List[str] = []
            raw_texts_by_page: Dict[int, str] = {}
            
            for page_num, page in enumerate(reader.pages, start=1):
                raw_text = page.extract_text()
                if raw_text and raw_text.strip():
                    raw_texts_by_page[page_num] = raw_text
                    # Usar las primeras 5 páginas como muestra para detección de idioma
                    if page_num <= 5:
                        text_sample_parts.append(raw_text)
            
            text_sample = "\n".join(text_sample_parts) if text_sample_parts else None
            
            # Resolver metadatos estructurados UNA VEZ por PDF (no por página)
            resolved_meta = self.metadata_extractor.resolve(
                filename=pdf_path.name,
                source_folder=source_folder,
                pdf_path=pdf_path,
                text_sample=text_sample,
            )
            
            for page_num, raw_text in raw_texts_by_page.items():
                # Limpiar texto
                clean_text = self.text_cleaner.clean_text(raw_text)
                
                # Crear StructuredMetadata por página (campos resueltos + page info)
                doc = ProcessedDocument(
                    text=clean_text,
                    metadata=StructuredMetadata(
                        filename=pdf_path.name,
                        source_folder=source_folder,
                        page_number=page_num,
                        total_pages=total_pages,
                        **resolved_meta,
                    )
                )
                
                documents.append(doc)
                logger.debug(f"✓ Página {page_num}/{total_pages} procesada ({doc.char_count} chars)")
            
            logger.info(f"✓ {pdf_path.name} completado: {len(documents)} páginas extraídas")
            return documents
        
        except Exception as e:
            logger.error(f"✗ Error procesando {pdf_path.name}: {str(e)}")
            raise
    
    
    def chunk_documents(self, documents: List[ProcessedDocument], 
                       chunk_size: int = 1000, 
                       chunk_overlap: int = 200) -> List[DocumentChunk]:
        """
        Divide documentos en chunks semánticos usando RecursiveCharacterTextSplitter.
        
        Esta función aplica una estrategia de chunking inteligente que:
        - Divide primero por párrafos (\n\n)
        - Luego por líneas (\n) si el chunk es muy grande
        - Como último recurso, por frases (. ! ?)
        - Nunca corta palabras a la mitad
        
        Args:
            documents: Lista de documentos a dividir en chunks
            chunk_size: Tamaño objetivo en tokens (~4 chars por token)
            chunk_overlap: Solapamiento entre chunks (en tokens)
            
        Returns:
            Lista de chunks semánticos con metadatos enriquecidos
            
        Example:
            >>> extractor = PDFExtractor("data/raw_pdfs")
            >>> docs = extractor.process_all_pdfs()
            >>> chunks = extractor.chunk_documents(docs, chunk_size=1000)
        """
        logger.info(f"🔪 Iniciando chunking semántico de {len(documents)} documentos")
        logger.info(f"   - Tamaño objetivo: {chunk_size} tokens (~{chunk_size * 4} caracteres)")
        logger.info(f"   - Solapamiento: {chunk_overlap} tokens")
        
        # Configurar separadores jerárquicos (de más a menos estructural)
        separators = [
            "\n\n",  # 1. Párrafos (prioridad máxima)
            "\n",    # 2. Líneas
            ". ",    # 3. Frases con punto (espacio evita decimales como 3.14)
            "! ",    # 4. Frases con exclamación
            "? ",    # 5. Frases con interrogación
            "; ",    # 6. Cláusulas
            ", ",    # 7. Sub-cláusulas
            " ",     # 8. Palabras (último recurso)
        ]
        
        # Crear splitter con configuración semántica
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size * 4,        # Convertir tokens a caracteres
            chunk_overlap=chunk_overlap * 4,  # Solapamiento en caracteres
            separators=separators,
            length_function=len,              # Función para medir longitud
            is_separator_regex=False          # Separadores son literales
        )
        
        all_chunks: List[DocumentChunk] = []
        
        for doc in documents:
            # Dividir el texto del documento
            raw_chunks = splitter.split_text(doc.text)
            
            logger.debug(f"Documento '{doc.metadata.filename}' (p.{doc.metadata.page_number}): "
                        f"{len(raw_chunks)} chunks generados")
            
            # Filtrar chunks demasiado cortos (< 10 caracteres)
            valid_chunks = [c for c in raw_chunks if len(c.strip()) >= 10]
            
            if len(valid_chunks) < len(raw_chunks):
                logger.debug(f"   Descartados {len(raw_chunks) - len(valid_chunks)} chunks cortos "
                           f"(<10 chars) del documento '{doc.metadata.filename}' (p.{doc.metadata.page_number})")
            
            # Crear objetos DocumentChunk con metadatos
            for idx, chunk_text in enumerate(valid_chunks):
                chunk = DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    text=chunk_text,
                    chunk_index=idx,
                    total_chunks=len(valid_chunks),
                    metadata=doc.metadata  # Heredar metadatos del documento
                )
                all_chunks.append(chunk)
        
        logger.info(f"✅ Chunking completado: {len(all_chunks)} chunks generados")
        logger.info(f"   - Promedio: {len(all_chunks) / len(documents):.1f} chunks por documento")
        
        # Estadísticas de tamaño
        avg_tokens = sum(c.token_count for c in all_chunks) / len(all_chunks)
        logger.info(f"   - Tamaño promedio: {avg_tokens:.0f} tokens/chunk")
        
        return all_chunks
    
    
    def process_all_pdfs(self, apply_chunking: bool = False,
                        chunk_size: int = 1000,
                        chunk_overlap: int = 200) -> Union[List[ProcessedDocument], Dict[str, List]]:
        """
        Procesa todos los PDFs encontrados en la carpeta de entrada (recursivamente).
        
        Args:
            apply_chunking: Si True, aplica chunking semántico a los documentos
            chunk_size: Tamaño objetivo de cada chunk en tokens (default: 1000)
            chunk_overlap: Solapamiento entre chunks en tokens (default: 200)
        
        Returns:
            Si apply_chunking=False: Lista de documentos procesados
            Si apply_chunking=True: Dict con {"documents": List[ProcessedDocument], 
                                              "chunks": List[DocumentChunk]}
        """
        all_documents: List[ProcessedDocument] = []
        
        # Buscar todos los PDFs (recursivamente)
        pdf_files = list(self.input_folder.rglob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No se encontraron archivos PDF en {self.input_folder}")
            return {"documents": [], "chunks": []} if apply_chunking else []
        
        logger.info(f"🚀 Iniciando procesamiento de {len(pdf_files)} archivos PDF")
        
        for pdf_path in pdf_files:
            try:
                docs = self.extract_from_pdf(pdf_path)
                all_documents.extend(docs)
            except Exception as e:
                logger.error(f"Saltando {pdf_path.name} debido a error: {e}")
                continue
        
        logger.info(f"✅ Procesamiento completado: {len(all_documents)} páginas extraídas en total")
        
        # Si se solicita chunking, aplicarlo
        if apply_chunking:
            all_chunks = self.chunk_documents(
                all_documents, 
                chunk_size=chunk_size, 
                chunk_overlap=chunk_overlap
            )
            return {"documents": all_documents, "chunks": all_chunks}
        
        return all_documents
    
    
    @staticmethod
    def save_to_json(documents: Union[List[ProcessedDocument], List[DocumentChunk]], 
                     output_path: Path | str) -> None:
        """
        Guarda documentos o chunks procesados en formato JSON.
        
        Args:
            documents: Lista de documentos o chunks procesados
            output_path: Ruta del archivo JSON de salida
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convertir a diccionarios serializables
        data = [doc.dict() for doc in documents]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Datos guardados en: {output_path}")
        logger.info(f"   - Total elementos: {len(documents)}")
        logger.info(f"   - Tamaño del archivo: {output_path.stat().st_size / 1024:.2f} KB")
