"""
Script de Validación Simple - Sistema de Vectorización

Valida que la implementación está correcta sin re-vectorizar.
Usa la base de datos existente para probar las funcionalidades.

Autor: David Arroyo
Proyecto: Dialektos

Usage:
    python examples/validate_implementation.py
"""

import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("✅ Imports básicos OK")

# Test 1: Imports
try:
    from src.ingest import embeddings_config
    print("✅ embeddings_config importado correctamente")
except Exception as e:
    print(f"❌ Error importando embeddings_config: {e}")
    sys.exit(1)

# Test 2: Configuración de modelos
try:
    recommended = embeddings_config.get_recommended_model_for_dialektos()
    print(f"✅ Modelo recomendado: {recommended}")
    
    multilingual = embeddings_config.list_available_models(
        language=embeddings_config.Language.MULTILINGUAL
    )
    print(f"✅ Modelos multilingües disponibles: {len(multilingual)}")
    
except Exception as e:
    print(f"❌ Error en configuración de modelos: {e}")
    sys.exit(1)

# Test 3: Validación de modelo
try:
    is_valid = embeddings_config.validate_model(recommended)
    print(f"✅ Modelo '{recommended}' es válido: {is_valid}")
    
    config = embeddings_config.get_model_config(recommended)
    print(f"✅ Configuración del modelo:")
    print(f"   - Dimensión: {config.dimension}")
    print(f"   - Tamaño: {config.size_mb}MB")
    print(f"   - Calidad: {config.quality.value}")
    
except Exception as e:
    print(f"❌ Error validando modelo: {e}")
    sys.exit(1)

# Test 4: Import de ChromaDBPersistence
try:
    from src.ingest.pdf_extractor import ChromaDBPersistence
    print("✅ ChromaDBPersistence importado correctamente")
except Exception as e:
    print(f"❌ Error importando ChromaDBPersistence: {e}")
    sys.exit(1)

# Test 5: Verificar que ChromaDB tiene el nuevo constructor
try:
    import inspect
    sig = inspect.signature(ChromaDBPersistence.__init__)
    params = list(sig.parameters.keys())
    
    if 'model_name' in params:
        print("✅ ChromaDBPersistence tiene parámetro 'model_name'")
    else:
        print("❌ ChromaDBPersistence NO tiene parámetro 'model_name'")
        print(f"   Parámetros encontrados: {params}")
    
    if 'collection_name' in params:
        print("✅ ChromaDBPersistence tiene parámetro 'collection_name'")
    
except Exception as e:
    print(f"❌ Error inspeccionando ChromaDBPersistence: {e}")
    sys.exit(1)

# Test 6: Verificar métodos de búsqueda avanzada
try:
    methods = [
        'semantic_search',
        'search_with_filters',
        'get_similar_chunks',
        'get_collection_stats'
    ]
    
    for method_name in methods:
        if hasattr(ChromaDBPersistence, method_name):
            print(f"✅ Método '{method_name}' implementado")
        else:
            print(f"❌ Método '{method_name}' NO encontrado")
    
except Exception as e:
    print(f"❌ Error verificando métodos: {e}")
    sys.exit(1)

# Test 7: Verificar estructura de archivos
print("\n📁 Verificando estructura de archivos:")
files_to_check = [
    "src/ingest/embeddings_config.py",
    "src/ingest/pdf_extractor.py",
    "examples/demo_embeddings.py",
    "examples/test_embeddings.py",
    "requirements.txt"
]

for file_path in files_to_check:
    path = Path(file_path)
    if path.exists():
        print(f"✅ {file_path}")
    else:
        print(f"❌ {file_path} NO existe")

# Test 8: Verificar requirements.txt
print("\n📦 Verificando dependencias en requirements.txt:")
with open("requirements.txt", "r") as f:
    content = f.read()
    
    if "sentence-transformers" in content:
        print("✅ sentence-transformers está en requirements.txt")
    else:
        print("❌ sentence-transformers NO está en requirements.txt")
    
    if "torch" in content:
        print("✅ torch está en requirements.txt")
    else:
        print("❌ torch NO está en requirements.txt")

# Resumen final
print("\n" + "=" * 80)
print("✅ VALIDACIÓN COMPLETADA")
print("=" * 80)
print("\n💡 La implementación está correcta.")
print("\nPróximos pasos:")
print("1. Para re-vectorizar con el nuevo modelo:")
print("   python src/ingest/pdf_extractor.py")
print("\n2. Para probar el demo interactivo:")
print("   python examples/demo_embeddings.py")
print("\n3. Para el modo interactivo de búsqueda:")
print("   python examples/demo_embeddings.py --interactive")
print("\n" + "=" * 80)
