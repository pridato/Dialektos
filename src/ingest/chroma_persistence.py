"""
Persistencia ChromaDB Optimizada - Sistema RAG Dialektos

Este módulo implementa la persistencia de chunks en ChromaDB con
optimizaciones de performance mediante batch processing.

Clase:
    ChromaDBPersistence: Gestor optimizado de persistencia para ChromaDB

Optimizaciones:
    - Batch processing para inserción eficiente
    - Progress bars con tqdm
    - Retry logic para robustez
    - Manejo mejorado de errores

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Optional

from .models import DocumentChunk


logger = logging.getLogger(__name__)


class ChromaDBPersistence:
    """
    Gestor de persistencia optimizado para ChromaDB con batch processing.
    
    Esta clase maneja la conexión con ChromaDB y la inserción eficiente de chunks
    con embeddings generados por Sentence Transformers. Incluye optimizaciones
    de performance mediante procesamiento por lotes.
    
    Attributes:
        client: Cliente persistente de ChromaDB
        collection: Colección para almacenar documentos
        model_name: Nombre del modelo de embeddings utilizado
        persist_directory: Directorio de persistencia de datos
        
    Example:
        >>> db = ChromaDBPersistence(
        ...     model_name="paraphrase-multilingual-mpnet-base-v2"
        ... )
        >>> db.add_chunks(chunks, batch_size=32, show_progress=True)
        >>> results = db.semantic_search("¿Qué es una matriz?", n_results=3)
    """
    
    def __init__(
        self, 
        persist_directory: Path | str = Path("data/chroma_db"),
        model_name: str = "paraphrase-multilingual-mpnet-base-v2",
        collection_name: str = "dialektos_documents"
    ):
        """
        Inicializa la conexión con ChromaDB usando un modelo de embeddings personalizado.
        
        Args:
            persist_directory: Directorio donde se persisten los datos
            model_name: Nombre del modelo de Sentence Transformers a usar.
                       Default: "paraphrase-multilingual-mpnet-base-v2"
            collection_name: Nombre de la colección en ChromaDB
            
        Raises:
            ImportError: Si chromadb o sentence-transformers no están instalados
            ValueError: Si el modelo especificado no es válido
        """
        try:
            import chromadb
            from chromadb.config import Settings
            from chromadb.utils import embedding_functions
            
            # Guardar configuración
            self.persist_directory = Path(persist_directory)
            self.model_name = model_name
            self.collection_name = collection_name
            
            # Crear directorio si no existe
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            
            # Inicializar cliente de ChromaDB
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Configurar función de embedding personalizada
            logger.info(f"🔄 Configurando modelo de embeddings: {model_name}")
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model_name
            )
            
            # Crear o recuperar colección con embedding function personalizada
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}  # Usar similitud coseno
            )
            
            logger.info(f"✅ ChromaDB inicializado correctamente")
            logger.info(f"   📁 Directorio: {self.persist_directory}")
            logger.info(f"   🤖 Modelo: {model_name}")
            logger.info(f"   📚 Colección: {collection_name}")
            logger.info(f"   📊 Elementos existentes: {self.collection.count()}")
            
        except ImportError as e:
            if "chromadb" in str(e):
                logger.error("❌ chromadb no está instalado. Ejecuta: pip install chromadb")
            elif "sentence" in str(e):
                logger.error("❌ sentence-transformers no está instalado. Ejecuta: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"❌ Error al inicializar ChromaDB: {str(e)}")
            raise
    
    
    def _insert_with_retry(
        self, 
        documents: List[str], 
        metadatas: List[Dict], 
        ids: List[str],
        max_retries: int = 3
    ) -> bool:
        """
        Inserta un batch con retry logic.
        
        Args:
            documents: Lista de textos
            metadatas: Lista de metadatos
            ids: Lista de IDs únicos
            max_retries: Número máximo de reintentos
            
        Returns:
            True si la inserción fue exitosa, False en caso contrario
        """
        for attempt in range(max_retries):
            try:
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"⚠️ Error en batch (intento {attempt + 1}/{max_retries}). "
                                 f"Reintentando en {wait_time}s... Error: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Error al insertar batch después de {max_retries} intentos: {str(e)}")
                    return False
        return False
    
    
    def add_chunks(
        self, 
        chunks: List[DocumentChunk],
        batch_size: int = 32,
        show_progress: bool = True,
        max_retries: int = 3
    ) -> None:
        """
        Añade chunks a ChromaDB con batch processing optimizado.
        
        Esta versión optimizada divide los chunks en batches para mejorar
        la eficiencia y proporciona feedback visual del progreso.
        
        Args:
            chunks: Lista de chunks a persistir
            batch_size: Tamaño del batch (default: 32, óptimo para Sentence Transformers)
            show_progress: Mostrar barra de progreso (default: True)
            max_retries: Intentos de retry por batch (default: 3)
            
        Raises:
            Exception: Si hay errores críticos en la inserción
        """
        if not chunks:
            logger.warning("⚠️ No hay chunks para agregar a ChromaDB")
            return
        
        logger.info(f"📥 Insertando {len(chunks)} chunks en ChromaDB...")
        logger.info(f"   - Batch size: {batch_size}")
        logger.info(f"   - Total batches: {(len(chunks) + batch_size - 1) // batch_size}")
        
        # Dividir en batches
        batches = [chunks[i:i+batch_size] for i in range(0, len(chunks), batch_size)]
        
        # Estadísticas
        successful_batches = 0
        failed_batches = 0
        total_chunks_inserted = 0
        start_time = time.time()
        
        # Intentar importar tqdm para progress bar
        try:
            from tqdm import tqdm
            iterator = tqdm(batches, desc="Insertando chunks", disable=not show_progress)
        except ImportError:
            logger.warning("⚠️ tqdm no instalado. Instala con: pip install tqdm")
            iterator = batches
            if show_progress:
                logger.info("Progress: Procesando batches...")
        
        # Procesar batches
        for batch_idx, batch in enumerate(iterator, 1):
            # Preparar datos del batch
            documents = [chunk.text for chunk in batch]
            metadatas = [chunk.metadata.dict() for chunk in batch]
            ids = [chunk.chunk_id for chunk in batch]
            
            # Insertar batch con retry
            success = self._insert_with_retry(documents, metadatas, ids, max_retries)
            
            if success:
                successful_batches += 1
                total_chunks_inserted += len(batch)
            else:
                failed_batches += 1
                logger.error(f"❌ Batch {batch_idx}/{len(batches)} falló después de {max_retries} intentos")
            
            # Log de progreso si no hay tqdm
            if not show_progress and batch_idx % 10 == 0:
                logger.info(f"   Progreso: {batch_idx}/{len(batches)} batches procesados")
        
        # Estadísticas finales
        elapsed_time = time.time() - start_time
        chunks_per_second = total_chunks_inserted / elapsed_time if elapsed_time > 0 else 0
        
        logger.info(f"\n✅ Inserción completada:")
        logger.info(f"   - Chunks insertados: {total_chunks_inserted}/{len(chunks)}")
        logger.info(f"   - Batches exitosos: {successful_batches}/{len(batches)}")
        logger.info(f"   - Batches fallidos: {failed_batches}")
        logger.info(f"   - Tiempo total: {elapsed_time:.2f}s")
        logger.info(f"   - Velocidad: {chunks_per_second:.1f} chunks/s")
        logger.info(f"   - Total elementos en DB: {self.collection.count()}")
        
        if failed_batches > 0:
            logger.warning(f"⚠️ {failed_batches} batches fallaron. Revisa los logs para más detalles.")
    
    
    def query(self, query_text: str, n_results: int = 3, 
              filter_metadata: Optional[Dict] = None) -> Dict:
        """
        Busca los chunks más similares a una consulta (método legacy).
        
        NOTA: Este método se mantiene por compatibilidad. Para nuevas
        implementaciones, usar semantic_search() que retorna resultados
        en formato más estructurado.
        
        Args:
            query_text: Texto de búsqueda
            n_results: Número de resultados a retornar
            filter_metadata: Filtros opcionales (ej: {"source_folder": "Algebra"})
            
        Returns:
            Diccionario con resultados y metadatos en formato ChromaDB
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=filter_metadata
        )
        
        return results
    
    
    def semantic_search(
        self, 
        query: str, 
        n_results: int = 5,
        min_similarity: float = 0.0
    ) -> List[Dict]:
        """
        Búsqueda semántica avanzada con scores de similitud normalizados.
        
        Este método realiza una búsqueda semántica y retorna los resultados
        en un formato estructurado y fácil de usar, incluyendo scores de
        similitud normalizados entre 0 y 1.
        
        Args:
            query: Texto de búsqueda (pregunta o frase)
            n_results: Número máximo de resultados a retornar (default: 5)
            min_similarity: Score mínimo de similitud (0-1). Resultados con
                          score menor serán filtrados (default: 0.0)
        
        Returns:
            Lista de diccionarios con la estructura:
            [
                {
                    "chunk_id": str,
                    "text": str,
                    "metadata": dict,
                    "score": float (0-1, donde 1 es máxima similitud),
                    "distance": float (distancia coseno original)
                },
                ...
            ]
            
        Example:
            >>> db = ChromaDBPersistence()
            >>> results = db.semantic_search("¿Qué es álgebra lineal?", n_results=3)
            >>> for r in results:
            ...     print(f"[{r['score']:.2f}] {r['text'][:100]}...")
        """
        if not query or not query.strip():
            logger.warning("⚠️ Query vacío proporcionado a semantic_search")
            return []
        
        try:
            # Realizar búsqueda en ChromaDB
            raw_results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Extraer datos
            ids = raw_results['ids'][0] if raw_results['ids'] else []
            documents = raw_results['documents'][0] if raw_results['documents'] else []
            metadatas = raw_results['metadatas'][0] if raw_results['metadatas'] else []
            distances = raw_results['distances'][0] if raw_results['distances'] else []
            
            # Estructurar resultados
            structured_results = []
            for idx, (chunk_id, text, metadata, distance) in enumerate(
                zip(ids, documents, metadatas, distances)
            ):
                # Convertir distancia coseno a score de similitud (1 - distance)
                # ChromaDB usa distancia coseno donde 0 = idéntico, 2 = opuesto
                similarity_score = 1.0 - (distance / 2.0)
                
                # Filtrar por similitud mínima
                if similarity_score < min_similarity:
                    continue
                
                structured_results.append({
                    "chunk_id": chunk_id,
                    "text": text,
                    "metadata": metadata,
                    "score": round(similarity_score, 4),
                    "distance": round(distance, 4),
                    "rank": idx + 1
                })
            
            logger.debug(f"🔍 Búsqueda semántica: {len(structured_results)} resultados "
                        f"(query: '{query[:50]}...')")
            
            return structured_results
            
        except Exception as e:
            logger.error(f"❌ Error en semantic_search: {str(e)}")
            return []
    
    
    def search_with_filters(
        self,
        query: str,
        filters: Dict[str, str],
        n_results: int = 5
    ) -> List[Dict]:
        """
        Búsqueda semántica con filtros de metadata.
        
        Permite realizar búsquedas restringidas a documentos específicos
        filtrando por sus metadatos (carpeta, archivo, página, etc.).
        
        Args:
            query: Texto de búsqueda
            filters: Filtros de metadata. Ejemplos:
                    - {"source_folder": "Algebra"}
                    - {"filename": "Tema1_Matrices.pdf"}
                    - {"page_number": 5}
            n_results: Número máximo de resultados
            
        Returns:
            Lista de diccionarios con resultados filtrados (mismo formato
            que semantic_search)
            
        Example:
            >>> # Buscar solo en documentos de Álgebra
            >>> results = db.search_with_filters(
            ...     query="vectores y matrices",
            ...     filters={"source_folder": "Algebra"},
            ...     n_results=3
            ... )
        """
        if not query or not query.strip():
            logger.warning("⚠️ Query vacío proporcionado a search_with_filters")
            return []
        
        try:
            # Realizar búsqueda con filtros
            raw_results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filters  # ChromaDB usa 'where' para filtros
            )
            
            # Estructurar resultados (mismo formato que semantic_search)
            ids = raw_results['ids'][0] if raw_results['ids'] else []
            documents = raw_results['documents'][0] if raw_results['documents'] else []
            metadatas = raw_results['metadatas'][0] if raw_results['metadatas'] else []
            distances = raw_results['distances'][0] if raw_results['distances'] else []
            
            structured_results = []
            for idx, (chunk_id, text, metadata, distance) in enumerate(
                zip(ids, documents, metadatas, distances)
            ):
                similarity_score = 1.0 - (distance / 2.0)
                
                structured_results.append({
                    "chunk_id": chunk_id,
                    "text": text,
                    "metadata": metadata,
                    "score": round(similarity_score, 4),
                    "distance": round(distance, 4),
                    "rank": idx + 1
                })
            
            logger.debug(f"🔍 Búsqueda filtrada: {len(structured_results)} resultados "
                        f"(filtros: {filters})")
            
            return structured_results
            
        except Exception as e:
            logger.error(f"❌ Error en search_with_filters: {str(e)}")
            return []
    
    
    def get_similar_chunks(
        self,
        chunk_id: str,
        n_results: int = 5,
        include_self: bool = False
    ) -> List[Dict]:
        """
        Encuentra chunks similares a un chunk específico.
        
        Útil para explorar contenido relacionado o encontrar chunks
        duplicados/similares en la base de datos.
        
        Args:
            chunk_id: ID del chunk de referencia
            n_results: Número de chunks similares a retornar
            include_self: Si True, incluye el chunk original en resultados
            
        Returns:
            Lista de chunks similares (mismo formato que semantic_search)
            
        Example:
            >>> # Encontrar chunks similares a uno específico
            >>> similar = db.get_similar_chunks(
            ...     chunk_id="abc-123-def",
            ...     n_results=5
            ... )
        """
        try:
            # Obtener el chunk original
            result = self.collection.get(ids=[chunk_id])
            
            if not result['documents']:
                logger.warning(f"⚠️ Chunk {chunk_id} no encontrado")
                return []
            
            # Usar el texto del chunk como query
            query_text = result['documents'][0]
            
            # Buscar similares
            similar = self.semantic_search(
                query=query_text,
                n_results=n_results + (0 if include_self else 1)
            )
            
            # Filtrar el chunk original si no se desea incluir
            if not include_self:
                similar = [chunk for chunk in similar if chunk['chunk_id'] != chunk_id]
            
            # Limitar a n_results
            similar = similar[:n_results]
            
            logger.debug(f"🔍 Encontrados {len(similar)} chunks similares a {chunk_id}")
            
            return similar
            
        except Exception as e:
            logger.error(f"❌ Error en get_similar_chunks: {str(e)}")
            return []
    
    
    def get_collection_stats(self) -> Dict:
        """
        Obtiene estadísticas de la colección.
        
        Returns:
            Diccionario con estadísticas:
            {
                "total_chunks": int,
                "model_name": str,
                "collection_name": str,
                "persist_directory": str,
                "unique_files": int,
                "unique_folders": list
            }
            
        Example:
            >>> stats = db.get_collection_stats()
            >>> print(f"Total chunks: {stats['total_chunks']}")
            >>> print(f"Archivos únicos: {stats['unique_files']}")
        """
        try:
            count = self.collection.count()
            
            # Obtener todos los metadatos para estadísticas
            all_data = self.collection.get()
            metadatas = all_data['metadatas']
            
            # Extraer información única
            unique_files = set()
            unique_folders = set()
            
            for metadata in metadatas:
                if 'filename' in metadata:
                    unique_files.add(metadata['filename'])
                if 'source_folder' in metadata:
                    unique_folders.add(metadata['source_folder'])
            
            stats = {
                "total_chunks": count,
                "model_name": self.model_name,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory),
                "unique_files": len(unique_files),
                "unique_folders": sorted(list(unique_folders))
            }
            
            logger.debug(f"📊 Estadísticas: {count} chunks, {len(unique_files)} archivos")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error al obtener estadísticas: {str(e)}")
            return {
                "total_chunks": 0,
                "model_name": self.model_name,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory),
                "unique_files": 0,
                "unique_folders": []
            }
    
    
    def reset_collection(self) -> None:
        """
        Elimina todos los datos de la colección (usar con precaución).
        
        ADVERTENCIA: Esta operación es irreversible. Todos los embeddings
        y metadatos serán eliminados permanentemente.
        """
        logger.warning("⚠️ Eliminando todos los datos de ChromaDB...")
        self.client.delete_collection(self.collection_name)
        
        # Recrear colección con la misma configuración
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("✅ Colección reiniciada")
