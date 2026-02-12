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
from src.brain.llm_client import query_llm, query_llm_with_history
from src.brain.memory import ConversationMemory
from src.brain.user_profile import build_enriched_system_prompt


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

REWRITE_SYSTEM_PROMPT: str = (
    "Tu ÚNICA tarea es reformular la última pregunta del usuario como una "
    "pregunta AUTOCONTENIDA, incorporando el contexto necesario del historial "
    "de conversación.\n\n"
    "REGLAS:\n"
    "1. Devuelve SOLO la pregunta reformulada, sin explicaciones ni prefijos.\n"
    "2. Si la pregunta ya es autocontenida, devuélvela tal cual.\n"
    "3. Resuelve pronombres y referencias implícitas (e.g. 'sus', 'eso', "
    "'lo anterior') usando el historial.\n"
    "4. Mantén el idioma original del usuario.\n"
    "5. No respondas la pregunta, solo reformúlala."
)


# ─── Clase Retriever ─────────────────────────────────────────

class Retriever:
    """
    Orquestador del flujo RAG: búsqueda semántica → prompt → LLM.

    Conecta ChromaDB (vector store) con el LLM (GPT-4o mini) mediante
    un prompt estricto que fuerza al modelo a responder solo con el
    contexto de los apuntes del alumno.

    Soporta conversaciones multi-turno gracias a ``ConversationMemory``
    y query rewriting automático para preguntas de seguimiento.

    La inyección de dependencias en ``__init__`` permite pasar una
    instancia mock de ``ChromaDBPersistence`` para testing.

    Attributes:
        db: Instancia de ChromaDBPersistence para búsqueda semántica.
        memory: Historial conversacional con ventana deslizante.

    Example:
        >>> retriever = Retriever()
        >>> r1 = retriever.retrieve_and_query("¿Qué es un espacio vectorial?")
        >>> r2 = retriever.retrieve_and_query("¿Y cuáles son sus propiedades?")
        >>> # r2 recuerda que "sus" se refiere a espacios vectoriales
    """

    def __init__(
        self,
        db: Optional[ChromaDBPersistence] = None,
        max_turns: int = 5,
    ) -> None:
        """
        Inicializa el Retriever con una conexión a ChromaDB y memoria.

        Args:
            db: Instancia de ChromaDBPersistence. Si es None, crea una
                con la configuración por defecto. Pasar una instancia
                explícita es útil para testing o configuraciones custom.
            max_turns: Número máximo de turnos de conversación a retener
                en memoria (default: 5).
        """
        self.db: ChromaDBPersistence = db or ChromaDBPersistence()
        self.memory: ConversationMemory = ConversationMemory(
            max_turns=max_turns,
        )
        logger.info("Retriever inicializado con memoria conversacional")

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

    def _rewrite_query(
        self,
        pregunta: str,
        history: List[Dict[str, str]],
    ) -> str:
        """
        Reformula una pregunta de seguimiento como pregunta autocontenida.

        Usa el LLM para resolver pronombres y referencias implícitas
        (e.g. "¿Y sus propiedades?" → "¿Cuáles son las propiedades
        de un espacio vectorial?"), de modo que la búsqueda semántica
        en ChromaDB encuentre chunks relevantes.

        Solo se ejecuta cuando hay historial previo.  En el primer
        turno la pregunta ya es autocontenida y no se reescribe.

        Args:
            pregunta: Pregunta original del usuario (posiblemente ambigua).
            history: Historial de mensajes previos (role + content).

        Returns:
            Pregunta reformulada como texto autocontenido.
        """
        try:
            rewritten: str = query_llm_with_history(
                pregunta=f"Reformula esta pregunta: {pregunta}",
                history=history,
                system_prompt=REWRITE_SYSTEM_PROMPT,
                temperature=0.0,
                max_tokens=150,
            )
            logger.info(
                f"  Query rewriting: '{pregunta[:50]}' → '{rewritten[:50]}'"
            )
            return rewritten.strip()

        except Exception as e:
            logger.warning(f"  Query rewriting falló: {e}. Usando original.")
            return pregunta

    def clear_memory(self) -> None:
        """
        Reinicia el historial de conversación.

        Útil para iniciar una nueva sesión de estudio sin arrastrar
        contexto de preguntas anteriores.
        """
        self.memory.clear()
        logger.info("Memoria conversacional reiniciada")

    def retrieve_and_query(
        self,
        pregunta: str,
        *,
        n_chunks: int = 3,
        min_similarity: float = 0.4,
    ) -> RAGResponse:
        """
        Busca contexto en ChromaDB y consulta al LLM con él.

        Flujo completo con memoria conversacional:
            0. Si hay historial, reescribe la query (query rewriting).
            1. Búsqueda semántica en ChromaDB (top ``n_chunks``).
            2. Si no hay resultados: retorna respuesta de rechazo.
            3. Si hay resultados: formatea contexto, construye prompt
               enriquecido, consulta al LLM con historial.
            4. Empaqueta todo en un ``RAGResponse`` validado.
            5. Guarda el turno en memoria.

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
            >>> r1 = retriever.retrieve_and_query("¿Qué es una derivada?")
            >>> r2 = retriever.retrieve_and_query("¿Y cómo se calcula?")
            >>> # r2 busca "cómo se calcula una derivada" en ChromaDB
        """
        if not pregunta or not pregunta.strip():
            raise ValueError("La pregunta no puede estar vacía.")

        logger.info(f"RAG query: '{pregunta[:80]}...'")

        # ── 0. Query rewriting (si hay historial) ────────────
        history: List[Dict[str, str]] = self.memory.get_messages()
        search_query: str = pregunta

        if not self.memory.is_first_turn:
            search_query = self._rewrite_query(pregunta, history)
            logger.info(f"  Query reescrita para búsqueda: '{search_query[:80]}'")

        # ── 1. Búsqueda semántica ────────────────────────────
        chunks: List[Dict[str, Any]] = self.db.semantic_search(
            query=search_query,
            n_results=n_chunks,
            min_similarity=min_similarity,
        )

        logger.info(f"  Chunks recuperados: {len(chunks)}")

        # ── 2. Sin contexto → rechazo estricto ───────────────
        if not chunks:
            logger.warning("  Sin contexto relevante. Respondiendo con rechazo.")
            # Guardar en memoria incluso sin contexto (para continuidad)
            self.memory.add_user_message(pregunta)
            self.memory.add_assistant_message(NO_CONTEXT_MESSAGE)
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

        # ── 5. Enriquecer system prompt con perfil del usuario ────
        enriched_system_prompt: str = build_enriched_system_prompt(RAG_SYSTEM_PROMPT)

        # ── 6. Consultar LLM con historial ───────────────────
        answer: str = query_llm_with_history(
            enriched_prompt,
            history=history,
            system_prompt=enriched_system_prompt,
            temperature=0.3,  # Más determinista para RAG
        )

        # ── 7. Guardar turno en memoria ─────────────────────
        self.memory.add_user_message(pregunta)
        self.memory.add_assistant_message(answer)

        # ── 8. Empaquetar respuesta ─────────────────────────
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
            f"max_score={sources[0].score:.2f}, "
            f"memoria={len(self.memory)} turnos"
        )

        return response


# ─── REPL de prueba ──────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Dialektos — RAG Chat con Memoria Conversacional")
    print("  Comandos:  'salir'  |  'reset' (limpiar memoria)")
    print("=" * 60)

    try:
        rag = Retriever()
    except Exception as e:
        print(f"\n✗ Error al inicializar: {e}")
        raise SystemExit(1)

    print(f"\n  DB cargada: {rag.db.collection.count()} chunks disponibles")
    print(f"  Memoria: hasta {rag.memory.max_turns} turnos")
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

        if pregunta.lower() == "reset":
            rag.clear_memory()
            print("\n  Memoria limpiada. Nueva conversación.")
            continue

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
                    f"min score: {min(scores):.2f} | "
                    f"memoria: {len(rag.memory)} turnos]"
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
