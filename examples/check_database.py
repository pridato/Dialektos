"""
Script para revisar el contenido de la base de datos existente
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import chromadb
    from chromadb.config import Settings
    
    print("\n📊 REVISANDO BASE DE DATOS EXISTENTE\n")
    print("=" * 80)
    
    # Conectar a ChromaDB
    CHROMA_DIR = Path("data/chroma_db")
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Listar colecciones
    collections = client.list_collections()
    print(f"\n📚 Colecciones encontradas: {len(collections)}")
    
    for col in collections:
        print(f"\n🗂️  Colección: {col.name}")
        print(f"   - Total chunks: {col.count()}")
        
        if col.count() > 0:
            # Obtener una muestra
            sample = col.get(limit=5)
            
            print(f"   - IDs de muestra: {sample['ids'][:2]}")
            
            if sample['metadatas']:
                print(f"\n   📋 Metadatos de muestra:")
                meta = sample['metadatas'][0]
                for key, value in meta.items():
                    print(f"      {key}: {value}")
            
            if sample['documents']:
                print(f"\n   📄 Texto de muestra:")
                text = sample['documents'][0]
                preview = text[:200] + "..." if len(text) > 200 else text
                print(f"      {preview}")
    
    print("\n" + "=" * 80)
    print("✅ Base de datos revisada correctamente")
    print("\n💡 Tienes datos existentes que podemos migrar al nuevo modelo")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
