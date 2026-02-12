"""
Retrieval System — Búsqueda semántica + LLM (RAG)

Orquesta el flujo completo de Retrieval-Augmented Generation:
    1. Recibe la pregunta del usuario.
    2. Busca los chunks más relevantes en ChromaDB.
    3. Formatea el contexto e inyecta en un prompt estricto.
    4. Envía al LLM y devuelve una respuesta validada (Pydantic).

Modo estricto: el LLM solo responde con información de los apuntes.
Si no hay contexto suficiente, rechaza la pregunta explícitamente.

Componentes:
    - RetrievedChunk: modelo Pydantic de un chunk recuperado.
    - RAGResponse: modelo Pydantic de la respuesta completa.
    - Retriever: clase principal que orquesta el flujo RAG.

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.ingest.chroma_persistence import ChromaDBPersistence
from src.brain.llm_client import query_llm


logger = logging.getLogger(__name__)


# ─── Modelos Pydantic ────────────────────────────────────────

class RetrievedChunk(BaseModel):
    """
    Chunk recuperado de ChromaDB con su score de similitud.

    Refleja exactamente la estructura que devuelve
    ``ChromaDBPersistence.semantic_search()``, pero validada
    con Pydantic para garantizar consistencia en el pipeline.

    Attributes:
        chunk_id: Identificador único del chunk (hash SHA-256 truncado).
        text: Contenido textual del fragmento.
        metadata: Metadatos del documento origen (archivo, página, etc.).
        score: Similitud coseno normalizada (0-1, donde 1 = idéntico).
        distance: Distancia coseno original de ChromaDB.
        rank: Posición en el ranking de resultados (1-indexed).
    """
    chunk_id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: float = Field(..., ge=0.0, le=1.0)
    distance: float = Field(..., ge=0.0)
    rank: int = Field(..., ge=1)


class RAGResponse(BaseModel):
    """
    Respuesta completa del sistema RAG.

    Encapsula la respuesta del LLM junto con las fuentes utilizadas
    y metadatos del proceso de retrieval, facilitando la trazabilidad
    y la presentación en el frontend.

    Attributes:
        answer: Texto de la respuesta del LLM.
        sources: Lista de chunks utilizados como contexto.
        had_context: True si se encontraron chunks relevantes.
        query: Pregunta original del usuario.
        n_chunks_retrieved: Número de chunks inyectados al prompt.
    """
    answer: str
    sources: List[RetrievedChunk] = Field(default_factory=list)
    had_context: bool = False
    query: str = ""
    n_chunks_retrieved: int = Field(default=0, ge=0)


# ─── Configuración RAG ──────────────────────────────────────

NO_CONTEXT_MESSAGE: str = "No tengo información en tus apuntes sobre esto."

RAG_SYSTEM_PROMPT: str = (
    "Eres Dialektos, un asistente de estudio universitario especializado "
    "en Ciencia de Datos, Matemáticas y Física.\n\n"
    "INSTRUCCIONES:\n"
    "1. Se te proporcionará CONTEXTO extraído de los apuntes del alumno. "
    "Este contexto puede estar en INGLÉS u otro idioma, pero tú SIEMPRE "
    "respondes en ESPAÑOL.\n"
    "2. BASA tu respuesta en la información del contexto proporcionado. "
    "Sintetiza, traduce y explica el contenido de los fragmentos.\n"
    "3. Si el contexto proporcionado NO tiene relación alguna con la "
    "pregunta, responde: 'No tengo información en tus apuntes sobre esto.'\n"
    "4. NO inventes datos ni cifras que no aparezcan en el contexto.\n"
    "5. Cita la fuente (archivo y página) cuando sea posible.\n"
    "6. Sé claro, riguroso y pedagógico."
)

RAG_USER_TEMPLATE: str = (
    "--- CONTEXTO (Apuntes del alumno) ---\n"
    "{context}\n"
    "--- FIN CONTEXTO ---\n\n"
    "Pregunta: {question}"
)


# ─── Clase Retriever ─────────────────────────────────────────

class Retriever:
    """
    Orquestador del flujo RAG: búsqueda semántica → prompt → LLM.

    Conecta ChromaDB (vector store) con el LLM (GPT-4o mini) mediante
    un prompt estricto que fuerza al modelo a responder solo con el
    contexto de los apuntes del alumno.

    La inyección de dependencias en ``__init__`` permite pasar una
    instancia mock de ``ChromaDBPersistence`` para testing.

    Attributes:
        db: Instancia de ChromaDBPersistence para búsqueda semántica.

    Example:
        >>> retriever = Retriever()
        >>> response = retriever.retrieve_and_query("¿Qué es una matriz?")
        >>> print(response.answer)
        >>> for src in response.sources:
        ...     print(f"  [{src.score:.2f}] {src.metadata.get('filename')}")
    """

    def __init__(self, db: Optional[ChromaDBPersistence] = None) -> None:
        """
        Inicializa el Retriever con una conexión a ChromaDB.

        Args:
            db: Instancia de ChromaDBPersistence. Si es None, crea una
                con la configuración por defecto. Pasar una instancia
                explícita es útil para testing o configuraciones custom.
        """
        self.db: ChromaDBPersistence = db or ChromaDBPersistence()
        logger.info("Retriever inicializado correctamente")

    @staticmethod
    def _format_context(chunks: List[Dict[str, Any]]) -> str:
        """
        Convierte una lista de chunks en texto estructurado para el prompt.

        Cada chunk se presenta con su metadata (archivo, página, score)
        para que el LLM pueda citar fuentes y el usuario pueda verificar.

        Args:
            chunks: Lista de dicts devueltos por ``semantic_search()``.
                    Cada dict contiene: chunk_id, text, metadata, score,
                    distance, rank.

        Returns:
            Texto formateado listo para inyectar en el prompt.

        Example:
            >>> context = Retriever._format_context(chunks)
            >>> print(context)
            [Fuente 1 | Similitud: 0.85 | Archivo: Calculo.pdf, p.12]
            "Texto del chunk..."
        """
        if not chunks:
            return ""

        blocks: List[str] = []

        for chunk in chunks:
            metadata: Dict[str, Any] = chunk.get("metadata", {})
            filename: str = metadata.get("filename", "Desconocido")
            page: Any = metadata.get("page_number", "?")
            score: float = chunk.get("score", 0.0)
            rank: int = chunk.get("rank", 0)

            header = (
                f"[Fuente {rank} | Similitud: {score:.2f} | "
                f"Archivo: {filename}, p.{page}]"
            )
            blocks.append(f"{header}\n{chunk['text']}")

        return "\n\n".join(blocks)

    def retrieve_and_query(
        self,
        pregunta: str,
        *,
        n_chunks: int = 3,
        min_similarity: float = 0.4,
    ) -> RAGResponse:
        """
        Busca contexto en ChromaDB y consulta al LLM con él.

        Flujo completo:
            1. Búsqueda semántica en ChromaDB (top ``n_chunks``).
            2. Si no hay resultados: retorna respuesta de rechazo.
            3. Si hay resultados: formatea contexto, construye prompt
               enriquecido, consulta al LLM.
            4. Empaqueta todo en un ``RAGResponse`` validado.

        Args:
            pregunta: La pregunta del usuario en texto plano.
            n_chunks: Número máximo de chunks a recuperar (default: 3).
            min_similarity: Umbral mínimo de similitud coseno (0-1).
                Chunks con score inferior se descartan (default: 0.4).

        Returns:
            RAGResponse con la respuesta, fuentes y metadatos del proceso.

        Raises:
            ValueError: Si la pregunta está vacía.

        Example:
            >>> retriever = Retriever()
            >>> resp = retriever.retrieve_and_query("¿Qué es una derivada?")
            >>> print(resp.answer)
            >>> print(f"Fuentes: {resp.n_chunks_retrieved}")
        """
        if not pregunta or not pregunta.strip():
            raise ValueError("La pregunta no puede estar vacía.")

        logger.info(f"RAG query: '{pregunta[:80]}...'")

        # ── 1. Búsqueda semántica ────────────────────────────
        chunks: List[Dict[str, Any]] = self.db.semantic_search(
            query=pregunta,
            n_results=n_chunks,
            min_similarity=min_similarity,
        )

        logger.info(f"  Chunks recuperados: {len(chunks)}")

        # ── 2. Sin contexto → rechazo estricto ───────────────
        if not chunks:
            logger.warning("  Sin contexto relevante. Respondiendo con rechazo.")
            return RAGResponse(
                answer=NO_CONTEXT_MESSAGE,
                sources=[],
                had_context=False,
                query=pregunta,
                n_chunks_retrieved=0,
            )

        # ── 3. Formatear contexto ────────────────────────────
        context: str = self._format_context(chunks)

        # ── 4. Construir prompt enriquecido ──────────────────
        enriched_prompt: str = RAG_USER_TEMPLATE.format(
            context=context,
            question=pregunta,
        )

        logger.debug(f"  Prompt enriquecido ({len(enriched_prompt)} chars)")

        # ── 5. Consultar LLM ────────────────────────────────
        answer: str = query_llm(
            enriched_prompt,
            system_prompt=RAG_SYSTEM_PROMPT,
            temperature=0.3,  # Más determinista para RAG
        )

        # ── 6. Empaquetar respuesta ─────────────────────────
        sources: List[RetrievedChunk] = [
            RetrievedChunk(**chunk) for chunk in chunks
        ]

        response = RAGResponse(
            answer=answer,
            sources=sources,
            had_context=True,
            query=pregunta,
            n_chunks_retrieved=len(sources),
        )

        logger.info(
            f"  RAG completado: {response.n_chunks_retrieved} fuentes, "
            f"max_score={sources[0].score:.2f}"
        )

        return response


# ─── REPL de prueba ──────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Dialektos — RAG Chat (Retrieval + LLM)")
    print("  Escribe 'salir' para terminar.")
    print("=" * 60)

    try:
        rag = Retriever()
    except Exception as e:
        print(f"\n✗ Error al inicializar: {e}")
        raise SystemExit(1)

    print(f"\n  DB cargada: {rag.db.collection.count()} chunks disponibles")
    print("-" * 60)

    while True:
        try:
            pregunta: str = input("\nTú: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nHasta luego.")
            break

        if pregunta.lower() in ("salir", "exit", "q"):
            print("\nHasta luego.")
            break

        if not pregunta:
            continue

        try:
            resp: RAGResponse = rag.retrieve_and_query(pregunta)

            # Mostrar fuentes
            if resp.had_context:
                scores = [s.score for s in resp.sources]
                print(
                    f"\n  [{resp.n_chunks_retrieved} chunks | "
                    f"max score: {max(scores):.2f} | "
                    f"min score: {min(scores):.2f}]"
                )
            else:
                print("\n  [Sin contexto relevante en la DB]")

            # Mostrar respuesta
            print(f"\nDialektos: {resp.answer}")

            # Mostrar fuentes citadas
            if resp.sources:
                print("\n  Fuentes:")
                for src in resp.sources:
                    filename = src.metadata.get("filename", "?")
                    page = src.metadata.get("page_number", "?")
                    print(f"    - {filename} (p.{page}) [{src.score:.2f}]")

        except ValueError as e:
            print(f"\n✗ Error: {e}")
        except Exception as e:
            print(f"\n✗ Error inesperado: {e}")
