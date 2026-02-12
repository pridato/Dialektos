#!/usr/bin/env python3
"""
Tests de Idempotencia - Sistema RAG Dialektos

Este módulo valida que el pipeline de ingesta sea idempotente:
ejecutar el pipeline múltiples veces no debe crear chunks duplicados.

Tests incluidos:
    - test_deterministic_chunk_ids: Valida generación consistente de IDs
    - test_filter_existing_chunks: Verifica filtrado de duplicados
    - test_idempotent_insertion: Valida inserción idempotente en ChromaDB
    - test_multiple_runs_no_duplicates: Test completo de ejecución múltiple

Uso:
    pytest tests/test_no_duplicates.py -v
    python tests/test_no_duplicates.py  # Ejecuta tests sin pytest

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import sys
import tempfile
import shutil
from pathlib import Path
from typing import List

# Añadir src al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest.models import DocumentChunk, DocumentMetadata
from src.ingest.chroma_persistence import ChromaDBPersistence


class TestChunkIDGeneration:
    """Tests para generación determinista de chunk IDs."""
    
    def test_same_content_same_id(self):
        """Mismo contenido debe generar el mismo ID."""
        metadata = DocumentMetadata(
            filename="test.pdf",
            source_folder="test",
            page_number=1,
            total_pages=1
        )
        
        # Crear dos chunks con el mismo texto
        chunk1 = DocumentChunk(
            text="Este es un texto de prueba",
            chunk_index=0,
            total_chunks=1,
            metadata=metadata
        )
        
        chunk2 = DocumentChunk(
            text="Este es un texto de prueba",
            chunk_index=0,
            total_chunks=1,
            metadata=metadata
        )
        
        assert chunk1.chunk_id == chunk2.chunk_id, \
            "Chunks con mismo contenido deben tener el mismo ID"
        print("✅ Test 1: Mismo contenido genera mismo ID")
    
    def test_different_content_different_id(self):
        """Contenido diferente debe generar IDs diferentes."""
        metadata = DocumentMetadata(
            filename="test.pdf",
            source_folder="test",
            page_number=1,
            total_pages=1
        )
        
        chunk1 = DocumentChunk(
            text="Texto uno",
            chunk_index=0,
            total_chunks=2,
            metadata=metadata
        )
        
        chunk2 = DocumentChunk(
            text="Texto dos",
            chunk_index=1,
            total_chunks=2,
            metadata=metadata
        )
        
        assert chunk1.chunk_id != chunk2.chunk_id, \
            "Chunks con diferente contenido deben tener IDs diferentes"
        print("✅ Test 2: Contenido diferente genera IDs diferentes")
    
    def test_id_independent_of_metadata(self):
        """ID debe ser independiente de los metadatos (solo basado en contenido)."""
        text = "Texto de prueba para verificar independencia"
        
        # Crear chunks con diferente metadata pero mismo texto
        chunk1 = DocumentChunk(
            text=text,
            chunk_index=0,
            total_chunks=1,
            metadata=DocumentMetadata(
                filename="file1.pdf",
                source_folder="folder1",
                page_number=1,
                total_pages=10
            )
        )
        
        chunk2 = DocumentChunk(
            text=text,
            chunk_index=5,
            total_chunks=10,
            metadata=DocumentMetadata(
                filename="file2.pdf",
                source_folder="folder2",
                page_number=99,
                total_pages=100
            )
        )
        
        assert chunk1.chunk_id == chunk2.chunk_id, \
            "ID debe depender solo del contenido, no de los metadatos"
        print("✅ Test 3: ID independiente de metadatos")


class TestFilterExistingChunks:
    """Tests para filtrado de chunks existentes."""
    
    def setup_test_db(self) -> tuple[ChromaDBPersistence, Path]:
        """Crea una base de datos temporal para testing."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_chroma_"))
        db = ChromaDBPersistence(
            persist_directory=temp_dir,
            collection_name="test_collection"
        )
        return db, temp_dir
    
    def cleanup_test_db(self, temp_dir: Path):
        """Limpia la base de datos temporal."""
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
    
    def test_filter_returns_only_new_chunks(self):
        """El filtro debe retornar solo chunks no existentes."""
        db, temp_dir = self.setup_test_db()
        
        try:
            metadata = DocumentMetadata(
                filename="test.pdf",
                source_folder="test",
                page_number=1,
                total_pages=1
            )
            
            # Crear chunks de prueba
            chunk1 = DocumentChunk(
                text="Chunk uno que ya existe",
                chunk_index=0,
                total_chunks=3,
                metadata=metadata
            )
            
            chunk2 = DocumentChunk(
                text="Chunk dos nuevo",
                chunk_index=1,
                total_chunks=3,
                metadata=metadata
            )
            
            chunk3 = DocumentChunk(
                text="Chunk tres nuevo",
                chunk_index=2,
                total_chunks=3,
                metadata=metadata
            )
            
            # Insertar chunk1 (simulando que ya existe)
            db.add_chunks([chunk1], skip_duplicates=False)
            
            # Intentar insertar los 3 chunks
            all_chunks = [chunk1, chunk2, chunk3]
            filtered = db._filter_existing_chunks(all_chunks)
            
            # Solo chunk2 y chunk3 deben retornarse
            assert len(filtered) == 2, \
                f"Esperaba 2 chunks nuevos, obtuve {len(filtered)}"
            
            filtered_ids = {c.chunk_id for c in filtered}
            assert chunk1.chunk_id not in filtered_ids, \
                "Chunk existente no debería estar en la lista filtrada"
            assert chunk2.chunk_id in filtered_ids, \
                "Chunk nuevo debería estar en la lista filtrada"
            assert chunk3.chunk_id in filtered_ids, \
                "Chunk nuevo debería estar en la lista filtrada"
            
            print("✅ Test 4: Filtro retorna solo chunks nuevos")
            
        finally:
            self.cleanup_test_db(temp_dir)


class TestIdempotentInsertion:
    """Tests para inserción idempotente."""
    
    def setup_test_db(self) -> tuple[ChromaDBPersistence, Path]:
        """Crea una base de datos temporal para testing."""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_chroma_"))
        db = ChromaDBPersistence(
            persist_directory=temp_dir,
            collection_name="test_collection"
        )
        return db, temp_dir
    
    def cleanup_test_db(self, temp_dir: Path):
        """Limpia la base de datos temporal."""
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
    
    def create_sample_chunks(self, count: int = 10) -> List[DocumentChunk]:
        """Crea chunks de muestra para testing."""
        metadata = DocumentMetadata(
            filename="test.pdf",
            source_folder="test",
            page_number=1,
            total_pages=1
        )
        
        chunks = []
        for i in range(count):
            chunk = DocumentChunk(
                text=f"Contenido de prueba número {i} con suficiente texto para ser válido",
                chunk_index=i,
                total_chunks=count,
                metadata=metadata
            )
            chunks.append(chunk)
        
        return chunks
    
    def test_first_insertion(self):
        """Primera inserción debe agregar todos los chunks."""
        db, temp_dir = self.setup_test_db()
        
        try:
            chunks = self.create_sample_chunks(5)
            initial_count = db.collection.count()
            
            # Primera inserción
            db.add_chunks(chunks)
            final_count = db.collection.count()
            
            assert final_count == initial_count + 5, \
                f"Esperaba {initial_count + 5} chunks, obtuve {final_count}"
            print("✅ Test 5: Primera inserción agrega todos los chunks")
            
        finally:
            self.cleanup_test_db(temp_dir)
    
    def test_second_insertion_adds_nothing(self):
        """Segunda inserción de los mismos chunks no debe agregar duplicados."""
        db, temp_dir = self.setup_test_db()
        
        try:
            chunks = self.create_sample_chunks(5)
            
            # Primera inserción
            db.add_chunks(chunks)
            count_after_first = db.collection.count()
            
            # Segunda inserción (mismos chunks)
            db.add_chunks(chunks)  # skip_duplicates=True por defecto
            count_after_second = db.collection.count()
            
            assert count_after_first == count_after_second, \
                f"Segunda inserción no debería crear duplicados. " \
                f"Primera: {count_after_first}, Segunda: {count_after_second}"
            
            print("✅ Test 6: Segunda inserción no crea duplicados (idempotente)")
            
        finally:
            self.cleanup_test_db(temp_dir)
    
    def test_multiple_runs(self):
        """Múltiples ejecuciones no deben incrementar el conteo."""
        db, temp_dir = self.setup_test_db()
        
        try:
            chunks = self.create_sample_chunks(5)
            
            counts = []
            for run in range(5):
                db.add_chunks(chunks)
                count = db.collection.count()
                counts.append(count)
                print(f"   Ejecución {run + 1}: {count} chunks")
            
            # Todos los conteos deben ser iguales
            assert all(c == counts[0] for c in counts), \
                f"Conteos inconsistentes entre ejecuciones: {counts}"
            
            assert counts[0] == 5, \
                f"Esperaba 5 chunks finales, obtuve {counts[0]}"
            
            print("✅ Test 7: Múltiples ejecuciones mantienen conteo estable")
            
        finally:
            self.cleanup_test_db(temp_dir)
    
    def test_partial_overlap(self):
        """Inserción con overlapping parcial debe agregar solo chunks nuevos."""
        db, temp_dir = self.setup_test_db()
        
        try:
            # Primera inserción: chunks 0-4
            first_batch = self.create_sample_chunks(5)
            db.add_chunks(first_batch)
            count_after_first = db.collection.count()
            
            # Segunda inserción: chunks 3-7 (overlap en 3 y 4)
            second_batch = self.create_sample_chunks(8)[3:]  # chunks 3, 4, 5, 6, 7
            db.add_chunks(second_batch)
            count_after_second = db.collection.count()
            
            # Debe agregar solo 3 chunks nuevos (5, 6, 7)
            expected = count_after_first + 3
            assert count_after_second == expected, \
                f"Esperaba {expected} chunks, obtuve {count_after_second}"
            
            print("✅ Test 8: Overlapping parcial inserta solo chunks nuevos")
            
        finally:
            self.cleanup_test_db(temp_dir)


def run_all_tests():
    """Ejecuta todos los tests."""
    print("=" * 80)
    print("🧪 TESTS DE IDEMPOTENCIA - SISTEMA RAG DIALEKTOS")
    print("=" * 80)
    print()
    
    all_passed = True
    
    try:
        # Test 1-3: Generación de IDs
        print("📦 Grupo 1: Generación Determinista de IDs")
        print("-" * 80)
        test_id = TestChunkIDGeneration()
        test_id.test_same_content_same_id()
        test_id.test_different_content_different_id()
        test_id.test_id_independent_of_metadata()
        print()
        
        # Test 4: Filtrado
        print("🔍 Grupo 2: Filtrado de Chunks Existentes")
        print("-" * 80)
        test_filter = TestFilterExistingChunks()
        test_filter.test_filter_returns_only_new_chunks()
        print()
        
        # Test 5-8: Idempotencia
        print("♻️  Grupo 3: Inserción Idempotente")
        print("-" * 80)
        test_idem = TestIdempotentInsertion()
        test_idem.test_first_insertion()
        test_idem.test_second_insertion_adds_nothing()
        test_idem.test_multiple_runs()
        test_idem.test_partial_overlap()
        print()
        
        print("=" * 80)
        print("✅ TODOS LOS TESTS PASARON")
        print("=" * 80)
        print()
        print("🎯 Conclusión:")
        print("   - Generación de IDs: Determinista ✅")
        print("   - Filtrado de duplicados: Funcional ✅")
        print("   - Idempotencia: Garantizada ✅")
        print()
        print("El sistema está listo para prevenir duplicados en producción.")
        
    except AssertionError as e:
        all_passed = False
        print()
        print("=" * 80)
        print("❌ TEST FALLÓ")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        
    except Exception as e:
        all_passed = False
        print()
        print("=" * 80)
        print("❌ ERROR INESPERADO")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
