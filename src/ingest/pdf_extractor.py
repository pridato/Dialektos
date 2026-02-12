"""
Script ETL: Extracción, Limpieza y Chunking de Texto desde PDFs

Este módulo es el punto de entrada principal del pipeline ETL modular.
Importa y re-exporta componentes de módulos especializados para mantener
backward compatibility con código existente.

Arquitectura Modular:
    - models.py: Modelos Pydantic (DocumentMetadata, ProcessedDocument, DocumentChunk)
    - text_cleaner.py: Limpieza de texto con RegEx
    - pdf_reader.py: Extracción y chunking de PDFs
    - chroma_persistence.py: Persistencia optimizada en ChromaDB

Pipeline completo:
    1. Extracción: Lee PDFs página por página
    2. Limpieza: Aplica RegEx para corregir artefactos del formato PDF
    3. Chunking: Divide texto en fragmentos semánticos (~1000 tokens)
    4. Enriquecimiento: Añade metadatos (archivo, carpeta, página, chunk_id)
    5. Persistencia: Guarda en JSON (debug) + ChromaDB (producción con batch processing)

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import logging
from pathlib import Path

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
# IMPORTS Y RE-EXPORTS (Backward Compatibility)
# ============================================================================

# Importar todos los componentes de los módulos especializados
from .models import DocumentMetadata, ProcessedDocument, DocumentChunk
from .text_cleaner import TextCleaner
from .pdf_reader import PDFExtractor
from .chroma_persistence import ChromaDBPersistence

# Re-exportar para backward compatibility
# Los imports existentes como "from src.ingest.pdf_extractor import ChromaDBPersistence"
# seguirán funcionando sin cambios
__all__ = [
    'DocumentMetadata',
    'ProcessedDocument',
    'DocumentChunk',
    'TextCleaner',
    'PDFExtractor',
    'ChromaDBPersistence',
]


# ============================================================================
# FUNCIÓN PRINCIPAL (CLI)
# ============================================================================

def main():
    """
    Función principal para ejecutar el ETL desde línea de comandos.
    
    Pipeline completo:
        1. Extracción de texto desde PDFs
        2. Limpieza de artefactos
        3. Chunking semántico inteligente
        4. Persistencia en JSON (debug) + ChromaDB (producción con optimizaciones)
    
    Usage:
        python -m src.ingest.pdf_extractor
    """
    logger.info("=" * 80)
    logger.info("ETL - EXTRACCIÓN Y CHUNKING DE TEXTO DESDE PDFs (MODULAR)")
    logger.info("=" * 80)
    
    # Configuración
    INPUT_FOLDER = Path("data/raw_pdfs")
    OUTPUT_DOCS = Path("data/processed/extracted_texts.json")
    OUTPUT_CHUNKS = Path("data/processed/chunks.json")
    CHROMA_DIR = Path("data/chroma_db")
    
    # Parámetros de chunking
    CHUNK_SIZE = 1000       # tokens (~4000 caracteres)
    CHUNK_OVERLAP = 200     # tokens de solapamiento
    
    # Modelo de embeddings (usar modelo multilingüe de alta calidad)
    EMBEDDING_MODEL = "paraphrase-multilingual-mpnet-base-v2"
    
    # Parámetros de optimización
    BATCH_SIZE = 32         # Tamaño óptimo para Sentence Transformers
    SHOW_PROGRESS = True    # Mostrar barra de progreso
    
    # =========================================================================
    # FASE 1: Extracción y Chunking
    # =========================================================================
    
    extractor = PDFExtractor(input_folder=INPUT_FOLDER)
    result = extractor.process_all_pdfs(
        apply_chunking=True,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    
    documents = result["documents"]
    chunks = result["chunks"]
    
    if not documents:
        logger.warning("No se procesaron documentos. Verifica la carpeta de entrada.")
        return
    
    # =========================================================================
    # FASE 2: Persistencia en JSON (para debug e inspección manual)
    # =========================================================================
    
    PDFExtractor.save_to_json(documents, output_path=OUTPUT_DOCS)
    PDFExtractor.save_to_json(chunks, output_path=OUTPUT_CHUNKS)
    
    # =========================================================================
    # FASE 3: Persistencia en ChromaDB (con batch processing optimizado)
    # =========================================================================
    
    try:
        db = ChromaDBPersistence(
            persist_directory=CHROMA_DIR,
            model_name=EMBEDDING_MODEL
        )
        
        # Opción: reiniciar la colección si existe (descomentar si necesario)
        # IMPORTANTE: Si cambias el modelo de embeddings, debes reiniciar la colección
        # db.reset_collection()
        
        # Inserción optimizada con batch processing
        db.add_chunks(
            chunks,
            batch_size=BATCH_SIZE,
            show_progress=SHOW_PROGRESS
        )
        
    except Exception as e:
        logger.error(f"❌ Error al persistir en ChromaDB: {str(e)}")
        logger.error("   Los chunks están disponibles en JSON para debug")
    
    # =========================================================================
    # FASE 4: Estadísticas Finales
    # =========================================================================
    
    total_chars = sum(doc.char_count for doc in documents)
    total_words = sum(doc.word_count for doc in documents)
    total_tokens = sum(chunk.token_count for chunk in chunks)
    avg_chunk_size = total_tokens / len(chunks) if chunks else 0
    
    logger.info("\n" + "=" * 80)
    logger.info("ESTADÍSTICAS FINALES DEL PIPELINE")
    logger.info("=" * 80)
    logger.info(f"📄 Documentos (páginas): {len(documents)}")
    logger.info(f"📝 Total caracteres: {total_chars:,}")
    logger.info(f"📖 Total palabras: {total_words:,}")
    logger.info("")
    logger.info(f"🔪 Chunks generados: {len(chunks)}")
    logger.info(f"📊 Tamaño promedio: {avg_chunk_size:.0f} tokens/chunk")
    logger.info(f"📦 Ratio chunks/doc: {len(chunks) / len(documents):.1f}")
    logger.info("")
    logger.info(f"💾 Archivos generados:")
    logger.info(f"   - Documentos: {OUTPUT_DOCS}")
    logger.info(f"   - Chunks: {OUTPUT_CHUNKS}")
    logger.info(f"   - ChromaDB: {CHROMA_DIR}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
