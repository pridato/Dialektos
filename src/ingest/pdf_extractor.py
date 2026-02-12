"""
Script ETL: Extracción, Limpieza y Chunking de Texto desde PDFs

Este módulo implementa un pipeline completo para convertir PDFs
(diseñados para impresoras) en texto estructurado y limpio (optimizado para máquinas).

Arquitectura del Pipeline:
    1. Extracción: Lee PDFs página por página
    2. Limpieza: Aplica RegEx para corregir artefactos del formato PDF
    3. Chunking: Divide texto en fragmentos semánticos (~1000 tokens)
    4. Enriquecimiento: Añade metadatos (archivo, carpeta, página, chunk_id)
    5. Persistencia: Guarda en JSON (debug) + ChromaDB (producción)

Características del Chunking Inteligente:
    - RecursiveCharacterTextSplitter con separadores jerárquicos
    - No corta frases a la mitad (respeta . ! ?)
    - Solapamiento de 200 tokens entre chunks (preserva contexto)
    - Metadatos completos para trazabilidad

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import re
import json
import logging
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, asdict

from pypdf import PdfReader
from pydantic import BaseModel, Field, validator
from langchain.text_splitter import RecursiveCharacterTextSplitter


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
# MODELOS DE DATOS (Pydantic)
# ============================================================================

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


class ProcessedDocument(BaseModel):
    """
    Documento procesado con texto limpio y metadatos.
    
    Attributes:
        text: Texto limpio y continuo (sin artefactos de PDF)
        metadata: Metadatos estructurados del documento
        char_count: Número de caracteres del texto limpio
        word_count: Número aproximado de palabras
    """
    text: str = Field(..., min_length=1, description="Texto procesado")
    metadata: DocumentMetadata
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
    
    Attributes:
        chunk_id: UUID único para identificación en ChromaDB
        text: Texto del fragmento (limpio y continuo)
        chunk_index: Posición del chunk dentro del documento (0-indexed)
        total_chunks: Total de chunks generados del documento original
        metadata: Metadatos heredados del documento original
        char_count: Número de caracteres del chunk
        token_count: Número aproximado de tokens (4 chars ≈ 1 token)
    """
    chunk_id: str = Field(..., description="UUID único del chunk")
    text: str = Field(..., min_length=10, description="Texto del chunk")
    chunk_index: int = Field(..., ge=0, description="Índice del chunk")
    total_chunks: int = Field(..., ge=1, description="Total de chunks del documento")
    metadata: DocumentMetadata
    char_count: int = Field(default=0, ge=0)
    token_count: int = Field(default=0, ge=0)
    
    def __init__(self, **data):
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


# ============================================================================
# CLASE PRINCIPAL: PDFExtractor
# ============================================================================

class PDFExtractor:
    """
    Extractor y limpiador de texto desde archivos PDF.
    
    Este extractor aplica una serie de transformaciones RegEx para
    corregir los artefactos introducidos por el formato PDF:
    
    - Arregla palabras cortadas con guiones al final de línea
    - Normaliza saltos de línea (mantiene párrafos reales)
    - Elimina ruido (espacios múltiples, caracteres invisibles)
    
    Example:
        >>> extractor = PDFExtractor(input_folder="data/raw_pdfs")
        >>> documents = extractor.process_all_pdfs()
        >>> extractor.save_to_json(documents, "data/processed/texts.json")
    """
    
    def __init__(self, input_folder: Path | str):
        """
        Inicializa el extractor.
        
        Args:
            input_folder: Carpeta raíz que contiene los PDFs a procesar
        """
        self.input_folder = Path(input_folder)
        
        if not self.input_folder.exists():
            raise FileNotFoundError(f"La carpeta {self.input_folder} no existe")
        
        logger.info(f"PDFExtractor inicializado. Carpeta de entrada: {self.input_folder}")
    
    
    # ========================================================================
    # MÉTODOS DE LIMPIEZA (Data Cleaning)
    # ========================================================================
    
    @staticmethod
    def fix_hyphenation(text: str) -> str:
        """
        A. Arregla palabras cortadas con guiones al final de línea.
        
        Problema:
            En un PDF, si "Algoritmo" no cabe en una línea:
            "Algo-\nritmo" → La IA lee dos palabras sin sentido
        
        Solución:
            Detecta el patrón [Guion] + [Salto de Línea] y lo elimina
        
        Args:
            text: Texto con posibles guiones de separación
            
        Returns:
            Texto con palabras unidas correctamente
            
        Example:
            >>> PDFExtractor.fix_hyphenation("Algo-\nritmo")
            'Algoritmo'
        """
        # Patrón: guion seguido de salto de línea (puede haber espacios)
        pattern = r'-\s*\n\s*'
        cleaned = re.sub(pattern, '', text)
        
        logger.debug(f"Hyphenation fix: {text.count(pattern)} correcciones aplicadas")
        return cleaned
    
    
    @staticmethod
    def normalize_line_breaks(text: str) -> str:
        """
        B. Normaliza saltos de línea respetando párrafos reales.
        
        Problema:
            Los PDFs ponen '\n' al final de cada línea visual.
            Para una máquina, eso parece el fin de una frase.
        
        Solución:
            - Saltos de línea simples (\n) → espacio en blanco
            - Saltos de línea dobles (\n\n) → mantener (indican cambio de párrafo)
        
        Args:
            text: Texto con saltos de línea arbitrarios
            
        Returns:
            Texto con frases continuas y párrafos preservados
        """
        # Primero, proteger los saltos dobles (párrafos reales)
        text = re.sub(r'\n\n+', '<<PARAGRAPH>>', text)
        
        # Reemplazar saltos simples por espacios
        text = re.sub(r'\n', ' ', text)
        
        # Restaurar los párrafos reales
        text = re.sub(r'<<PARAGRAPH>>', '\n\n', text)
        
        return text
    
    
    @staticmethod
    def remove_noise(text: str) -> str:
        """
        C. Elimina ruido: espacios múltiples, tabulaciones, caracteres invisibles.
        
        Problema:
            Dobles espacios, tabs, caracteres de control residuales.
        
        Solución:
            Colapsar cualquier secuencia de espacios en blanco en un solo espacio.
        
        Args:
            text: Texto con posible ruido
            
        Returns:
            Texto con espaciado normalizado
        """
        # Reemplazar múltiples espacios (incluyendo tabs) por un solo espacio
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Eliminar espacios al inicio y final de cada línea
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Eliminar más de dos saltos de línea consecutivos
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    
    def clean_text(self, raw_text: str) -> str:
        """
        Pipeline completo de limpieza de texto.
        
        Aplica las tres etapas de limpieza en orden:
            1. Arreglar guiones (hyphenation)
            2. Normalizar saltos de línea
            3. Eliminar ruido
        
        Args:
            raw_text: Texto extraído directamente del PDF
            
        Returns:
            Texto limpio y continuo, listo para procesamiento NLP
        """
        logger.debug("Iniciando pipeline de limpieza")
        
        # Etapa A: Hyphenation
        text = self.fix_hyphenation(raw_text)
        
        # Etapa B: Line Breaks
        text = self.normalize_line_breaks(text)
        
        # Etapa C: Noise Reduction
        text = self.remove_noise(text)
        
        logger.debug(f"Limpieza completada. Longitud final: {len(text)} caracteres")
        return text
    
    
    # ========================================================================
    # MÉTODOS DE CHUNKING (Semantic Splitting)
    # ========================================================================
    
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
            
            # Crear objetos DocumentChunk con metadatos
            for idx, chunk_text in enumerate(raw_chunks):
                chunk = DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    text=chunk_text,
                    chunk_index=idx,
                    total_chunks=len(raw_chunks),
                    metadata=doc.metadata  # Heredar metadatos del documento
                )
                all_chunks.append(chunk)
        
        logger.info(f"✅ Chunking completado: {len(all_chunks)} chunks generados")
        logger.info(f"   - Promedio: {len(all_chunks) / len(documents):.1f} chunks por documento")
        
        # Estadísticas de tamaño
        avg_tokens = sum(c.token_count for c in all_chunks) / len(all_chunks)
        logger.info(f"   - Tamaño promedio: {avg_tokens:.0f} tokens/chunk")
        
        return all_chunks
    
    
    # ========================================================================
    # MÉTODOS DE EXTRACCIÓN
    # ========================================================================
    
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
            
            for page_num, page in enumerate(reader.pages, start=1):
                # Extraer texto crudo
                raw_text = page.extract_text()
                
                if not raw_text or len(raw_text.strip()) == 0:
                    logger.warning(f"Página {page_num} de {pdf_path.name} está vacía. Saltando.")
                    continue
                
                # Limpiar texto
                clean_text = self.clean_text(raw_text)
                
                # Crear objeto con metadatos
                doc = ProcessedDocument(
                    text=clean_text,
                    metadata=DocumentMetadata(
                        filename=pdf_path.name,
                        source_folder=source_folder,
                        page_number=page_num,
                        total_pages=total_pages
                    )
                )
                
                documents.append(doc)
                logger.debug(f"✓ Página {page_num}/{total_pages} procesada ({doc.char_count} chars)")
            
            logger.info(f"✓ {pdf_path.name} completado: {len(documents)} páginas extraídas")
            return documents
        
        except Exception as e:
            logger.error(f"✗ Error procesando {pdf_path.name}: {str(e)}")
            raise
    
    
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
    
    
    # ========================================================================
    # MÉTODOS DE PERSISTENCIA
    # ========================================================================
    
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


# ============================================================================
# PERSISTENCIA EN CHROMADB
# ============================================================================

class ChromaDBPersistence:
    """
    Gestor de persistencia para ChromaDB con soporte para embeddings personalizados.
    
    Esta clase maneja la conexión con ChromaDB y la inserción de chunks
    con embeddings generados por Sentence Transformers. Soporta diferentes
    modelos configurables para optimizar calidad vs velocidad.
    
    Attributes:
        client: Cliente persistente de ChromaDB
        collection: Colección para almacenar documentos
        model_name: Nombre del modelo de embeddings utilizado
        persist_directory: Directorio de persistencia de datos
        
    Example:
        >>> db = ChromaDBPersistence(
        ...     model_name="paraphrase-multilingual-mpnet-base-v2"
        ... )
        >>> db.add_chunks(chunks)
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
    
    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        """
        Añade chunks a ChromaDB con embeddings automáticos.
        
        ChromaDB genera automáticamente los embeddings usando su modelo
        por defecto. Los metadatos se almacenan junto con cada chunk para
        permitir filtrado posterior.
        
        Args:
            chunks: Lista de chunks a persistir
        """
        if not chunks:
            logger.warning("⚠️ No hay chunks para agregar a ChromaDB")
            return
        
        logger.info(f"📥 Insertando {len(chunks)} chunks en ChromaDB...")
        
        # Preparar datos para ChromaDB
        documents = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata.dict() for chunk in chunks]
        ids = [chunk.chunk_id for chunk in chunks]
        
        try:
            # Insertar en ChromaDB (genera embeddings automáticamente)
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"✅ {len(chunks)} chunks persistidos exitosamente")
            logger.info(f"   - Total elementos en DB: {self.collection.count()}")
            
        except Exception as e:
            logger.error(f"❌ Error al insertar en ChromaDB: {str(e)}")
            raise
    
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
    
    
    # ========================================================================
    # MÉTODOS DE BÚSQUEDA AVANZADA
    # ========================================================================
    
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
                "unique_folders": set
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
        4. Persistencia en JSON (debug) + ChromaDB (producción)
    
    Usage:
        python pdf_extractor.py
    """
    logger.info("=" * 80)
    logger.info("ETL - EXTRACCIÓN Y CHUNKING DE TEXTO DESDE PDFs")
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
    
    extractor.save_to_json(documents, output_path=OUTPUT_DOCS)
    extractor.save_to_json(chunks, output_path=OUTPUT_CHUNKS)
    
    # =========================================================================
    # FASE 3: Persistencia en ChromaDB (para búsqueda vectorial)
    # =========================================================================
    
    try:
        db = ChromaDBPersistence(
            persist_directory=CHROMA_DIR,
            model_name=EMBEDDING_MODEL
        )
        
        # Opción: reiniciar la colección si existe (descomentar si necesario)
        # IMPORTANTE: Si cambias el modelo de embeddings, debes reiniciar la colección
        # db.reset_collection()
        
        db.add_chunks(chunks)
        
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
