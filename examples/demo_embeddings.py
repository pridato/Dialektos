"""
Demo Interactivo - Sistema de Vectorización con Embeddings

Este script demuestra las capacidades del sistema de búsqueda semántica
implementado con Sentence Transformers y ChromaDB.

Características demostradas:
1. Búsqueda semántica básica
2. Búsqueda con filtros de metadata
3. Exploración de chunks similares
4. Visualización de scores de similitud
5. Estadísticas de la colección

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo

Usage:
    python examples/demo_embeddings.py
"""

import sys
from pathlib import Path

# Añadir src al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest.pdf_extractor import ChromaDBPersistence
from src.ingest.embeddings_config import (
    get_recommended_model_for_dialektos,
    print_model_info,
    list_available_models,
    EmbeddingQuality
)
import logging


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger(__name__)


# ============================================================================
# FUNCIONES DE VISUALIZACIÓN
# ============================================================================

def print_header(text: str) -> None:
    """Imprime un encabezado decorado."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_separator() -> None:
    """Imprime un separador."""
    print("-" * 80)


def print_result(result: dict, show_full_text: bool = False) -> None:
    """
    Imprime un resultado de búsqueda de forma legible.
    
    Args:
        result: Diccionario con el resultado de búsqueda
        show_full_text: Si True, muestra el texto completo del chunk
    """
    score = result['score']
    text = result['text']
    metadata = result['metadata']
    
    # Barra de similitud visual
    bar_length = 20
    filled_length = int(bar_length * score)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    
    # Color basado en score (usando códigos ANSI)
    if score >= 0.8:
        color = '\033[92m'  # Verde
    elif score >= 0.6:
        color = '\033[93m'  # Amarillo
    else:
        color = '\033[91m'  # Rojo
    reset = '\033[0m'
    
    print(f"\n{color}Score: {score:.3f} [{bar}]{reset}")
    print(f"📄 Archivo: {metadata.get('filename', 'N/A')}")
    print(f"📁 Carpeta: {metadata.get('source_folder', 'N/A')}")
    print(f"📖 Página: {metadata.get('page_number', 'N/A')}/{metadata.get('total_pages', 'N/A')}")
    print(f"\n💬 Texto:")
    
    if show_full_text:
        print(f"   {text}")
    else:
        # Mostrar solo los primeros 300 caracteres
        preview = text[:300] + "..." if len(text) > 300 else text
        print(f"   {preview}")


# ============================================================================
# DEMOS
# ============================================================================

def demo_1_basic_search(db: ChromaDBPersistence) -> None:
    """
    Demo 1: Búsqueda semántica básica
    
    Demuestra la capacidad de encontrar contenido relevante usando
    lenguaje natural, incluso sin coincidencias exactas de palabras.
    """
    print_header("DEMO 1: Búsqueda Semántica Básica")
    
    queries = [
        "¿Qué es álgebra lineal?",
        "Explica las matrices y vectores",
        "¿Cómo se calculan probabilidades?",
    ]
    
    for query in queries:
        print(f"\n🔍 Query: \"{query}\"")
        print_separator()
        
        results = db.semantic_search(query, n_results=3)
        
        if not results:
            print("   ⚠️ No se encontraron resultados")
            continue
        
        for i, result in enumerate(results, 1):
            print(f"\n[Resultado {i}]")
            print_result(result, show_full_text=False)
        
        print()


def demo_2_filtered_search(db: ChromaDBPersistence) -> None:
    """
    Demo 2: Búsqueda con filtros de metadata
    
    Demuestra cómo restringir búsquedas a documentos específicos
    usando filtros de metadata.
    """
    print_header("DEMO 2: Búsqueda con Filtros")
    
    # Obtener estadísticas para saber qué filtros usar
    stats = db.get_collection_stats()
    folders = stats['unique_folders']
    
    print(f"\n📊 Carpetas disponibles: {folders}")
    
    # Ejemplo de búsqueda filtrada
    query = "matemáticas y ecuaciones"
    
    # Búsqueda sin filtro
    print(f"\n🔍 Búsqueda SIN filtro: \"{query}\"")
    print_separator()
    results_unfiltered = db.semantic_search(query, n_results=3)
    print(f"   ✓ Encontrados {len(results_unfiltered)} resultados")
    if results_unfiltered:
        print_result(results_unfiltered[0], show_full_text=False)
    
    # Búsqueda con filtro (si hay carpetas disponibles)
    if folders and len(folders) > 0:
        filter_folder = folders[0]
        print(f"\n🔍 Búsqueda CON filtro (carpeta='{filter_folder}'): \"{query}\"")
        print_separator()
        results_filtered = db.search_with_filters(
            query=query,
            filters={"source_folder": filter_folder},
            n_results=3
        )
        print(f"   ✓ Encontrados {len(results_filtered)} resultados en '{filter_folder}'")
        if results_filtered:
            print_result(results_filtered[0], show_full_text=False)


def demo_3_similar_chunks(db: ChromaDBPersistence) -> None:
    """
    Demo 3: Exploración de chunks similares
    
    Demuestra cómo encontrar contenido relacionado a partir de
    un chunk específico.
    """
    print_header("DEMO 3: Exploración de Chunks Similares")
    
    # Primero, hacer una búsqueda para obtener un chunk de referencia
    query = "vectores"
    results = db.semantic_search(query, n_results=1)
    
    if not results:
        print("   ⚠️ No hay chunks disponibles para esta demo")
        return
    
    reference_chunk = results[0]
    chunk_id = reference_chunk['chunk_id']
    
    print(f"\n📌 Chunk de referencia:")
    print_result(reference_chunk, show_full_text=False)
    
    print(f"\n🔍 Buscando chunks similares...")
    print_separator()
    
    similar_chunks = db.get_similar_chunks(
        chunk_id=chunk_id,
        n_results=3,
        include_self=False
    )
    
    print(f"\n✓ Encontrados {len(similar_chunks)} chunks similares:\n")
    
    for i, chunk in enumerate(similar_chunks, 1):
        print(f"[Similar {i}]")
        print_result(chunk, show_full_text=False)
        print()


def demo_4_similarity_threshold(db: ChromaDBPersistence) -> None:
    """
    Demo 4: Filtrado por umbral de similitud
    
    Demuestra cómo usar umbrales de similitud para filtrar
    resultados de baja calidad.
    """
    print_header("DEMO 4: Filtrado por Umbral de Similitud")
    
    query = "inteligencia artificial y machine learning"
    
    # Búsqueda sin umbral
    print(f"\n🔍 Query: \"{query}\"")
    print(f"\n📊 Sin umbral de similitud (min_similarity=0.0):")
    print_separator()
    
    results_no_threshold = db.semantic_search(
        query=query,
        n_results=5,
        min_similarity=0.0
    )
    
    print(f"   Resultados: {len(results_no_threshold)}")
    for r in results_no_threshold:
        print(f"   • Score: {r['score']:.3f}")
    
    # Búsqueda con umbral alto
    print(f"\n📊 Con umbral alto (min_similarity=0.7):")
    print_separator()
    
    results_high_threshold = db.semantic_search(
        query=query,
        n_results=5,
        min_similarity=0.7
    )
    
    print(f"   Resultados: {len(results_high_threshold)}")
    for r in results_high_threshold:
        print(f"   • Score: {r['score']:.3f}")
    
    print(f"\n💡 Interpretación:")
    print(f"   - Umbral 0.7+ es recomendado para RAG de alta precisión")
    print(f"   - Umbral 0.5+ es aceptable para búsqueda exploratoria")
    print(f"   - Scores < 0.5 suelen ser poco relevantes")


def demo_5_collection_stats(db: ChromaDBPersistence) -> None:
    """
    Demo 5: Estadísticas de la colección
    
    Muestra información general sobre el estado de la base de datos vectorial.
    """
    print_header("DEMO 5: Estadísticas de la Colección")
    
    stats = db.get_collection_stats()
    
    print(f"\n📊 RESUMEN DE LA COLECCIÓN")
    print_separator()
    print(f"🤖 Modelo de embeddings: {stats['model_name']}")
    print(f"📚 Nombre de colección: {stats['collection_name']}")
    print(f"📁 Directorio: {stats['persist_directory']}")
    print(f"\n📈 CONTENIDO")
    print_separator()
    print(f"📄 Total de chunks: {stats['total_chunks']}")
    print(f"📋 Archivos únicos: {stats['unique_files']}")
    print(f"📁 Carpetas: {len(stats['unique_folders'])}")
    
    if stats['unique_folders']:
        print(f"\n📂 Carpetas indexadas:")
        for folder in stats['unique_folders']:
            print(f"   • {folder}")


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """
    Ejecuta todas las demos del sistema de embeddings.
    """
    print("\n")
    print("🎯" * 40)
    print("\n  🤖 DIALEKTOS - DEMO DE SISTEMA DE VECTORIZACIÓN")
    print("  Sistema RAG Adaptativo con Sentence Transformers\n")
    print("🎯" * 40)
    
    # Mostrar información del modelo recomendado
    print("\n📚 Modelo Recomendado para Dialektos:")
    recommended_model = get_recommended_model_for_dialektos()
    print_model_info(recommended_model)
    
    # Inicializar conexión con ChromaDB
    print_header("Inicializando ChromaDB")
    
    try:
        db = ChromaDBPersistence(
            model_name=recommended_model,
            persist_directory="data/chroma_db"
        )
        
        # Verificar que hay datos
        stats = db.get_collection_stats()
        if stats['total_chunks'] == 0:
            print("\n⚠️ ADVERTENCIA: No hay chunks en la base de datos.")
            print("   Ejecuta primero: python src/ingest/pdf_extractor.py")
            return
        
        print(f"\n✅ Conectado exitosamente. {stats['total_chunks']} chunks disponibles.\n")
        
        # Ejecutar demos
        demo_1_basic_search(db)
        input("\n⏸️  Presiona ENTER para continuar a la siguiente demo...")
        
        demo_2_filtered_search(db)
        input("\n⏸️  Presiona ENTER para continuar a la siguiente demo...")
        
        demo_3_similar_chunks(db)
        input("\n⏸️  Presiona ENTER para continuar a la siguiente demo...")
        
        demo_4_similarity_threshold(db)
        input("\n⏸️  Presiona ENTER para continuar a la siguiente demo...")
        
        demo_5_collection_stats(db)
        
        # Conclusión
        print_header("Demo Completada")
        print("\n✨ Todas las funcionalidades han sido demostradas exitosamente.")
        print("\n💡 Próximos pasos:")
        print("   1. Integrar búsqueda semántica con el LLM (Módulo 2)")
        print("   2. Implementar sistema de retrieval con top-K chunks")
        print("   3. Añadir metadatos estructurados (asignatura, tipo, fecha)")
        print("\n" + "=" * 80 + "\n")
        
    except ImportError as e:
        print(f"\n❌ Error: Dependencias faltantes")
        print(f"   {str(e)}")
        print("\n💡 Instala las dependencias:")
        print("   pip install -r requirements.txt")
    
    except FileNotFoundError as e:
        print(f"\n❌ Error: Base de datos no encontrada")
        print(f"   {str(e)}")
        print("\n💡 Ejecuta primero el ETL para crear la base de datos:")
        print("   python src/ingest/pdf_extractor.py")
    
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()


# ============================================================================
# MODO INTERACTIVO
# ============================================================================

def interactive_mode():
    """
    Modo interactivo que permite al usuario hacer consultas personalizadas.
    """
    print_header("MODO INTERACTIVO")
    
    recommended_model = get_recommended_model_for_dialektos()
    
    try:
        db = ChromaDBPersistence(
            model_name=recommended_model,
            persist_directory="data/chroma_db"
        )
        
        stats = db.get_collection_stats()
        print(f"\n✅ Conectado. {stats['total_chunks']} chunks disponibles.")
        print("\n💡 Escribe tus consultas (escribe 'salir' para terminar):\n")
        
        while True:
            query = input("🔍 Query: ").strip()
            
            if query.lower() in ['salir', 'exit', 'quit']:
                print("\n👋 ¡Hasta luego!")
                break
            
            if not query:
                continue
            
            results = db.semantic_search(query, n_results=3)
            
            if not results:
                print("   ⚠️ No se encontraron resultados relevantes\n")
                continue
            
            print_separator()
            for i, result in enumerate(results, 1):
                print(f"\n[Resultado {i}]")
                print_result(result, show_full_text=False)
            
            print("\n" + "=" * 80 + "\n")
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Demo del sistema de vectorización de Dialektos"
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Modo interactivo (permite consultas personalizadas)"
    )
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    else:
        main()
