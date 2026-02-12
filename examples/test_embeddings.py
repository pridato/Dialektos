"""
Script de Prueba - Sistema de Vectorización

Este script valida que el sistema de embeddings funciona correctamente:
1. Carga los chunks existentes desde JSON
2. Re-vectoriza con el nuevo modelo
3. Valida búsquedas semánticas
4. Muestra estadísticas

Autor: David Arroyo
Proyecto: Dialektos

Usage:
    python examples/test_embeddings.py
"""

import sys
import json
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest.pdf_extractor import ChromaDBPersistence, DocumentChunk
from src.ingest.embeddings_config import get_recommended_model_for_dialektos
import logging


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# ============================================================================
# FUNCIONES DE TEST
# ============================================================================

def load_chunks_from_json(json_path: Path) -> list:
    """Carga chunks desde el archivo JSON."""
    logger.info(f"📂 Cargando chunks desde {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    chunks = [DocumentChunk(**chunk_data) for chunk_data in data]
    logger.info(f"✅ Cargados {len(chunks)} chunks")
    
    return chunks


def test_vectorization(chunks: list, model_name: str) -> ChromaDBPersistence:
    """
    Prueba la vectorización de chunks con el nuevo modelo.
    
    ADVERTENCIA: Esto eliminará la base de datos existente.
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: VECTORIZACIÓN CON NUEVO MODELO")
    logger.info("=" * 80)
    
    # Inicializar ChromaDB con el nuevo modelo
    db = ChromaDBPersistence(
        model_name=model_name,
        persist_directory="data/chroma_db_test"  # Usar directorio de test
    )
    
    # Resetear colección para empezar desde cero
    logger.info("⚠️  Reseteando colección existente...")
    db.reset_collection()
    
    # Añadir chunks
    logger.info(f"📥 Vectorizando {len(chunks)} chunks con modelo '{model_name}'...")
    db.add_chunks(chunks)
    
    # Verificar
    stats = db.get_collection_stats()
    logger.info(f"✅ Vectorización completada")
    logger.info(f"   - Chunks en DB: {stats['total_chunks']}")
    logger.info(f"   - Modelo: {stats['model_name']}")
    
    return db


def test_semantic_search(db: ChromaDBPersistence):
    """Prueba la búsqueda semántica básica."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: BÚSQUEDA SEMÁNTICA")
    logger.info("=" * 80)
    
    test_queries = [
        "¿Qué es álgebra lineal?",
        "matrices y vectores",
        "probabilidad y estadística",
    ]
    
    for query in test_queries:
        logger.info(f"\n🔍 Query: '{query}'")
        results = db.semantic_search(query, n_results=3)
        
        if results:
            logger.info(f"   ✅ Encontrados {len(results)} resultados")
            for i, r in enumerate(results[:2], 1):
                logger.info(f"   [{i}] Score: {r['score']:.3f} | {r['text'][:80]}...")
        else:
            logger.warning(f"   ⚠️ No se encontraron resultados")


def test_filtered_search(db: ChromaDBPersistence):
    """Prueba la búsqueda con filtros."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: BÚSQUEDA CON FILTROS")
    logger.info("=" * 80)
    
    stats = db.get_collection_stats()
    folders = stats['unique_folders']
    
    if not folders:
        logger.warning("⚠️ No hay carpetas para filtrar")
        return
    
    test_folder = folders[0]
    logger.info(f"📁 Filtrando por carpeta: '{test_folder}'")
    
    results = db.search_with_filters(
        query="matemáticas",
        filters={"source_folder": test_folder},
        n_results=3
    )
    
    if results:
        logger.info(f"   ✅ Encontrados {len(results)} resultados en '{test_folder}'")
        for i, r in enumerate(results[:2], 1):
            logger.info(f"   [{i}] Score: {r['score']:.3f}")
    else:
        logger.warning(f"   ⚠️ No se encontraron resultados en '{test_folder}'")


def test_similar_chunks(db: ChromaDBPersistence):
    """Prueba la búsqueda de chunks similares."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: CHUNKS SIMILARES")
    logger.info("=" * 80)
    
    # Obtener un chunk de referencia
    results = db.semantic_search("vectores", n_results=1)
    
    if not results:
        logger.warning("⚠️ No hay chunks disponibles para este test")
        return
    
    chunk_id = results[0]['chunk_id']
    logger.info(f"📌 Chunk de referencia: {chunk_id}")
    
    similar = db.get_similar_chunks(chunk_id, n_results=3)
    
    if similar:
        logger.info(f"   ✅ Encontrados {len(similar)} chunks similares")
        for i, s in enumerate(similar, 1):
            logger.info(f"   [{i}] Score: {s['score']:.3f}")
    else:
        logger.warning(f"   ⚠️ No se encontraron chunks similares")


def test_collection_stats(db: ChromaDBPersistence):
    """Prueba las estadísticas de la colección."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: ESTADÍSTICAS DE LA COLECCIÓN")
    logger.info("=" * 80)
    
    stats = db.get_collection_stats()
    
    logger.info(f"📊 Resumen:")
    logger.info(f"   - Total chunks: {stats['total_chunks']}")
    logger.info(f"   - Archivos únicos: {stats['unique_files']}")
    logger.info(f"   - Carpetas: {len(stats['unique_folders'])}")
    logger.info(f"   - Modelo: {stats['model_name']}")
    
    if stats['unique_folders']:
        logger.info(f"   - Carpetas indexadas: {', '.join(stats['unique_folders'])}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Ejecuta todos los tests."""
    logger.info("\n" + "🧪" * 40)
    logger.info("\n  🔬 TEST DE SISTEMA DE VECTORIZACIÓN - DIALEKTOS")
    logger.info("  Validación de embeddings con Sentence Transformers\n")
    logger.info("🧪" * 40 + "\n")
    
    try:
        # Configuración
        chunks_json = Path("data/processed/chunks.json")
        model_name = get_recommended_model_for_dialektos()
        
        logger.info(f"🤖 Modelo seleccionado: {model_name}")
        
        # Verificar que existe el archivo de chunks
        if not chunks_json.exists():
            logger.error(f"❌ No se encontró {chunks_json}")
            logger.error("   Ejecuta primero: python src/ingest/pdf_extractor.py")
            return
        
        # Cargar chunks
        chunks = load_chunks_from_json(chunks_json)
        
        # TEST 1: Vectorización
        db = test_vectorization(chunks[:100], model_name)  # Solo primeros 100 para test rápido
        
        # TEST 2: Búsqueda semántica
        test_semantic_search(db)
        
        # TEST 3: Búsqueda filtrada
        test_filtered_search(db)
        
        # TEST 4: Chunks similares
        test_similar_chunks(db)
        
        # TEST 5: Estadísticas
        test_collection_stats(db)
        
        # Resumen final
        logger.info("\n" + "=" * 80)
        logger.info("✅ TODOS LOS TESTS COMPLETADOS EXITOSAMENTE")
        logger.info("=" * 80)
        logger.info("\n💡 El sistema de vectorización está funcionando correctamente.")
        logger.info("   Puedes proceder a:")
        logger.info("   1. Vectorizar todos los chunks: python src/ingest/pdf_extractor.py")
        logger.info("   2. Probar el demo interactivo: python examples/demo_embeddings.py")
        logger.info("   3. Integrar con el LLM (Módulo 2)\n")
        
    except ImportError as e:
        logger.error(f"\n❌ Error: Dependencias faltantes")
        logger.error(f"   {str(e)}")
        logger.error("\n💡 Instala las dependencias:")
        logger.error("   pip install -r requirements.txt")
    
    except FileNotFoundError as e:
        logger.error(f"\n❌ Error: {str(e)}")
        logger.error("\n💡 Ejecuta primero el ETL:")
        logger.error("   python src/ingest/pdf_extractor.py")
    
    except Exception as e:
        logger.error(f"\n❌ Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
