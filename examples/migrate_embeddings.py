"""
Script de Migración - Actualizar Embeddings en Base de Datos Existente

Este script actualiza los embeddings de una base de datos ChromaDB existente
al nuevo modelo sin perder los datos.

IMPORTANTE: Este script:
1. Lee todos los chunks de la base de datos existente
2. Crea una nueva colección con el nuevo modelo de embeddings
3. Re-vectoriza todos los chunks
4. Reemplaza la colección antigua

Autor: David Arroyo
Proyecto: Dialektos

Usage:
    python examples/migrate_embeddings.py
"""

import sys
from pathlib import Path
import logging

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Migra la base de datos existente al nuevo modelo de embeddings."""
    
    print("\n" + "🔄" * 40)
    print("\n  🔄 MIGRACIÓN DE EMBEDDINGS - DIALEKTOS")
    print("  Actualizando base de datos existente al nuevo modelo\n")
    print("🔄" * 40 + "\n")
    
    try:
        import chromadb
        from chromadb.config import Settings
        from chromadb.utils import embedding_functions
        from src.ingest.embeddings_config import get_recommended_model_for_dialektos
        
        CHROMA_DIR = Path("data/chroma_db")
        OLD_COLLECTION = "dialektos_documents"
        NEW_MODEL = get_recommended_model_for_dialektos()
        
        logger.info(f"📁 Base de datos: {CHROMA_DIR}")
        logger.info(f"🤖 Nuevo modelo: {NEW_MODEL}")
        
        # Paso 1: Conectar a la base de datos existente
        logger.info("\n" + "=" * 80)
        logger.info("PASO 1: Leer base de datos existente")
        logger.info("=" * 80)
        
        client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Obtener colección existente
        try:
            old_collection = client.get_collection(name=OLD_COLLECTION)
            total_chunks = old_collection.count()
            logger.info(f"✅ Base de datos encontrada: {total_chunks} chunks")
        except Exception as e:
            logger.error(f"❌ No se pudo acceder a la colección: {e}")
            logger.info("\n💡 Solución: Ejecuta primero el ETL para crear la base de datos:")
            logger.info("   python src/ingest/pdf_extractor.py")
            return
        
        if total_chunks == 0:
            logger.warning("⚠️  La base de datos está vacía")
            logger.info("\n💡 Ejecuta el ETL para procesar PDFs:")
            logger.info("   python src/ingest/pdf_extractor.py")
            return
        
        # Paso 2: Extraer todos los datos
        logger.info("\n" + "=" * 80)
        logger.info("PASO 2: Extraer datos existentes")
        logger.info("=" * 80)
        
        logger.info(f"📤 Extrayendo {total_chunks} chunks...")
        all_data = old_collection.get()
        
        ids = all_data['ids']
        documents = all_data['documents']
        metadatas = all_data['metadatas']
        
        logger.info(f"✅ Datos extraídos:")
        logger.info(f"   - IDs: {len(ids)}")
        logger.info(f"   - Documentos: {len(documents)}")
        logger.info(f"   - Metadatos: {len(metadatas)}")
        
        # Mostrar muestra de datos
        if metadatas:
            unique_files = set(m.get('filename', 'N/A') for m in metadatas)
            logger.info(f"   - Archivos únicos: {len(unique_files)}")
            logger.info(f"   - Ejemplo: {list(unique_files)[:3]}")
        
        # Paso 3: Crear nueva colección con nuevo modelo
        logger.info("\n" + "=" * 80)
        logger.info("PASO 3: Crear colección con nuevo modelo de embeddings")
        logger.info("=" * 80)
        
        logger.info(f"⚠️  IMPORTANTE: La colección actual será reemplazada")
        response = input("\n¿Continuar con la migración? (sí/no): ").strip().lower()
        
        if response not in ['sí', 'si', 's', 'yes', 'y']:
            logger.info("❌ Migración cancelada por el usuario")
            return
        
        logger.info(f"\n🔄 Eliminando colección antigua...")
        client.delete_collection(name=OLD_COLLECTION)
        
        logger.info(f"🔄 Creando colección con modelo '{NEW_MODEL}'...")
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=NEW_MODEL
        )
        
        new_collection = client.get_or_create_collection(
            name=OLD_COLLECTION,
            embedding_function=embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"✅ Colección creada con nuevo modelo")
        
        # Paso 4: Re-vectorizar con el nuevo modelo
        logger.info("\n" + "=" * 80)
        logger.info("PASO 4: Re-vectorizar chunks con nuevo modelo")
        logger.info("=" * 80)
        
        logger.info(f"📥 Re-vectorizando {len(documents)} chunks...")
        logger.info(f"   Esto puede tomar varios minutos...")
        
        # Vectorizar en lotes de 100 para mostrar progreso
        BATCH_SIZE = 100
        total_batches = (len(documents) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, len(documents))
            
            batch_ids = ids[start_idx:end_idx]
            batch_docs = documents[start_idx:end_idx]
            batch_metas = metadatas[start_idx:end_idx]
            
            new_collection.add(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_metas
            )
            
            progress = (batch_idx + 1) / total_batches * 100
            logger.info(f"   Progreso: {progress:.1f}% ({end_idx}/{len(documents)} chunks)")
        
        # Paso 5: Verificar resultado
        logger.info("\n" + "=" * 80)
        logger.info("PASO 5: Verificar resultado")
        logger.info("=" * 80)
        
        final_count = new_collection.count()
        logger.info(f"✅ Chunks en nueva colección: {final_count}")
        
        if final_count == total_chunks:
            logger.info("✅ Todos los chunks migrados correctamente")
        else:
            logger.warning(f"⚠️  Diferencia detectada: {total_chunks} → {final_count}")
        
        # Paso 6: Probar búsqueda
        logger.info("\n" + "=" * 80)
        logger.info("PASO 6: Probar búsqueda con nuevo modelo")
        logger.info("=" * 80)
        
        test_query = "álgebra lineal"
        logger.info(f"\n🔍 Query de prueba: '{test_query}'")
        
        results = new_collection.query(
            query_texts=[test_query],
            n_results=3
        )
        
        if results['ids'][0]:
            logger.info(f"✅ Búsqueda funcional: {len(results['ids'][0])} resultados")
            
            # Mostrar primer resultado
            first_result = results['documents'][0][0]
            preview = first_result[:150] + "..." if len(first_result) > 150 else first_result
            logger.info(f"\n📄 Primer resultado:")
            logger.info(f"   {preview}")
        else:
            logger.warning("⚠️  Búsqueda no retornó resultados")
        
        # Resumen final
        logger.info("\n" + "=" * 80)
        logger.info("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        logger.info("=" * 80)
        logger.info(f"\n📊 Resumen:")
        logger.info(f"   - Chunks migrados: {final_count}")
        logger.info(f"   - Modelo anterior: all-MiniLM-L6-v2 (default)")
        logger.info(f"   - Modelo nuevo: {NEW_MODEL}")
        logger.info(f"   - Dimensión: 768 (antes: 384)")
        logger.info(f"   - Calidad: ALTA (antes: MEDIA)")
        
        logger.info(f"\n💡 Ahora puedes usar las nuevas funcionalidades:")
        logger.info(f"   1. Demo interactivo: python examples/demo_embeddings.py")
        logger.info(f"   2. Búsqueda avanzada con scores: db.semantic_search()")
        logger.info(f"   3. Filtros por metadata: db.search_with_filters()")
        logger.info("\n" + "=" * 80 + "\n")
        
    except ImportError as e:
        logger.error(f"\n❌ Error: Dependencias faltantes")
        logger.error(f"   {str(e)}")
        logger.error("\n💡 Instala las dependencias:")
        logger.error("   pip install sentence-transformers torch chromadb")
    
    except Exception as e:
        logger.error(f"\n❌ Error durante la migración: {str(e)}")
        import traceback
        traceback.print_exc()
        logger.error("\n💡 Si hay algún error, tu base de datos original está en:")
        logger.error("   data/chroma_db/")


if __name__ == "__main__":
    main()
