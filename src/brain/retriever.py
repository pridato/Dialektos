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
from src.brain.adversary import AdversarySession, QuestionType


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
        question_type: Tipo de pregunta detectado (CONCEPTUAL, FACTUAL, PROCEDURAL).
        adversary_activated: True si se activó el modo adversario para esta pregunta.
        adversary_depth: Profundidad actual del cuestionamiento socrático (0-5).
            Solo tiene valor si adversary_activated es True.
    """
    answer: str
    sources: List[RetrievedChunk] = Field(default_factory=list)
    had_context: bool = False
    query: str = ""
    n_chunks_retrieved: int = Field(default=0, ge=0)
    question_type: Optional[QuestionType] = None
    adversary_activated: bool = False
    adversary_depth: Optional[int] = Field(default=None, ge=0, le=5)


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
    "3. Si el contexto proporcionado tiene ALGUNA relación con la pregunta "
    "(aunque sea tangencial o parcial), intenta responder usando ese contexto. "
    "Solo responde 'No tengo información en tus apuntes sobre esto.' si el "
    "contexto es completamente irrelevante o no tiene ninguna conexión con la pregunta.\n"
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
        adversary_enabled: bool = True,
    ) -> None:
        """
        Inicializa el Retriever con una conexión a ChromaDB y memoria.

        Args:
            db: Instancia de ChromaDBPersistence. Si es None, crea una
                con la configuración por defecto. Pasar una instancia
                explícita es útil para testing o configuraciones custom.
            max_turns: Número máximo de turnos de conversación a retener
                en memoria (default: 5).
            adversary_enabled: Si se debe activar el modo adversario para
                preguntas conceptuales (default: True).
        """
        self.db: ChromaDBPersistence = db or ChromaDBPersistence()
        self.memory: ConversationMemory = ConversationMemory(
            max_turns=max_turns,
        )
        self.adversary_enabled: bool = adversary_enabled
        self.adversary_session: AdversarySession = AdversarySession()
        logger.info(
            f"Retriever inicializado con memoria conversacional "
            f"(adversario: {'activado' if adversary_enabled else 'desactivado'})"
        )

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
        Reinicia el historial de conversación y la sesión adversaria.

        Útil para iniciar una nueva sesión de estudio sin arrastrar
        contexto de preguntas anteriores.
        """
        self.memory.clear()
        self.adversary_session.reset()
        logger.info("Memoria conversacional y sesión adversaria reiniciadas")

    def retrieve_and_query(
        self,
        pregunta: str,
        *,
        n_chunks: int = 3,
        min_similarity: float = 0.25,
        adversary_mode: Optional[bool] = None,
    ) -> RAGResponse:
        """
        Busca contexto en ChromaDB y consulta al LLM con él.

        Flujo completo con memoria conversacional y modo adversario:
            0. Si el modo adversario está activo y hay una sesión activa,
               evaluar si se debe proporcionar contexto o continuar cuestionando.
            1. Si es una nueva pregunta conceptual, activar modo adversario.
            2. Si es factual/procedural o el adversario decide proporcionar contexto,
               buscar en ChromaDB y responder normalmente.
            3. Si el modo adversario está activo, generar pregunta socrática.

        Args:
            pregunta: La pregunta del usuario en texto plano.
            n_chunks: Número máximo de chunks a recuperar (default: 3).
            min_similarity: Umbral mínimo de similitud coseno (0-1).
                Chunks con score inferior se descartan (default: 0.25).
            adversary_mode: Si se debe usar el modo adversario para esta consulta.
                Si es None, usa la configuración del Retriever (default: None).

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

        # Determinar si el modo adversario está activo para esta consulta
        use_adversary: bool = (
            adversary_mode
            if adversary_mode is not None
            else self.adversary_enabled
        )

        logger.info(
            f"RAG query: '{pregunta[:80]}...' (adversario: {use_adversary})")

        # ── 0. Análisis del tipo de pregunta (siempre se hace para metadata) ──
        detected_question_type: QuestionType = (
            self.adversary_session.analyzer.analyze_question(pregunta)
        )

        # ── 1. Manejo del modo adversario ──────────────────────
        history: List[Dict[str, str]] = self.memory.get_messages()
        should_reset_adversary: bool = False
        adversary_activated: bool = False
        adversary_depth: Optional[int] = None

        # Si hay una sesión adversaria activa, evaluar si es una respuesta del usuario
        if use_adversary and self.adversary_session.state.is_active:
            # Esta es una respuesta del usuario a una pregunta socrática previa
            adversary_activated = True
            adversary_depth = self.adversary_session.state.question_depth + 1
            self.adversary_session.add_user_response(pregunta)

            # Evaluar si se debe proporcionar contexto ahora
            if self.adversary_session.should_provide_context():
                logger.info(
                    "Usuario demostró comprensión o alcanzó profundidad máxima. "
                    "Proporcionando contexto RAG."
                )
                # Continuar con búsqueda RAG normal (más abajo)
                # Resetear sesión adversaria después de proporcionar contexto
                should_reset_adversary = True
            else:
                # Continuar cuestionando
                logger.info(
                    f"Continuando cuestionamiento socrático "
                    f"(profundidad: {self.adversary_session.state.question_depth})"
                )
                socratic_question: str = (
                    self.adversary_session.generate_socratic_question(pregunta)
                )

                # Guardar en memoria
                self.memory.add_user_message(pregunta)
                self.memory.add_assistant_message(socratic_question)

                return RAGResponse(
                    answer=socratic_question,
                    sources=[],
                    had_context=False,
                    query=pregunta,
                    n_chunks_retrieved=0,
                    question_type=detected_question_type,
                    adversary_activated=True,
                    adversary_depth=self.adversary_session.state.question_depth,
                )

        # ── 2. Análisis de tipo de pregunta (si no hay sesión activa) ────
        elif use_adversary and not self.adversary_session.state.is_active:
            # Nueva entrada: analizar si es conceptual o afirmación
            if self.adversary_session.should_activate(pregunta):
                # Es conceptual o afirmación: activar modo adversario
                adversary_activated = True
                adversary_depth = 1
                if detected_question_type == QuestionType.ASSERTION:
                    logger.info(
                        "⚠️  AFIRMACIÓN peligrosa detectada. Activando modo adversario "
                        "para romper simplificaciones y profundizar conocimiento."
                    )
                else:
                    logger.info(
                        "Pregunta conceptual detectada. Activando modo adversario.")
                socratic_question: str = (
                    self.adversary_session.generate_socratic_question(pregunta)
                )

                # Guardar en memoria
                self.memory.add_user_message(pregunta)
                self.memory.add_assistant_message(socratic_question)

                return RAGResponse(
                    answer=socratic_question,
                    sources=[],
                    had_context=False,
                    query=pregunta,
                    n_chunks_retrieved=0,
                    question_type=detected_question_type,
                    adversary_activated=True,
                    adversary_depth=1,
                )
            # Si no es conceptual, continuar con RAG normal

        # ── 2. Query rewriting (si hay historial y no es modo adversario) ──
        search_query: str = pregunta

        if not self.memory.is_first_turn and not (
            use_adversary and self.adversary_session.state.is_active
        ):
            search_query = self._rewrite_query(pregunta, history)
            logger.info(
                f"  Query reescrita para búsqueda: '{search_query[:80]}'")

        # ── 4. Búsqueda semántica en ChromaDB ────────────────────
        chunks: List[Dict[str, Any]] = self.db.semantic_search(
            query=search_query,
            n_results=n_chunks,
            min_similarity=min_similarity,
        )

        logger.info(f"  Chunks recuperados: {len(chunks)}")

        # ── 5. Sin contexto → rechazo estricto ──────────────────────
        if not chunks:
            logger.warning(
                "  Sin contexto relevante. Respondiendo con rechazo.")
            # Guardar en memoria incluso sin contexto (para continuidad)
            self.memory.add_user_message(pregunta)
            self.memory.add_assistant_message(NO_CONTEXT_MESSAGE)

            # Resetear adversario si estaba activo
            if should_reset_adversary:
                self.adversary_session.reset()

            return RAGResponse(
                answer=NO_CONTEXT_MESSAGE,
                sources=[],
                had_context=False,
                query=pregunta,
                n_chunks_retrieved=0,
                question_type=detected_question_type,
                adversary_activated=adversary_activated,
                adversary_depth=adversary_depth,
            )

        # ── 6. Formatear contexto ───────────────────────────────────
        context: str = self._format_context(chunks)

        # ── 7. Construir prompt enriquecido ────────────────────────
        # Si venimos del modo adversario, usar la pregunta original
        question_for_rag: str = pregunta
        if use_adversary and should_reset_adversary:
            # Usar la pregunta original del adversario, no la última respuesta
            question_for_rag = self.adversary_session.state.original_question
            enriched_prompt: str = (
                "El estudiante ha demostrado comprensión del concepto. "
                "Ahora proporciona información adicional basada en los apuntes:\n\n"
                + RAG_USER_TEMPLATE.format(context=context,
                                           question=question_for_rag)
            )
        else:
            enriched_prompt: str = RAG_USER_TEMPLATE.format(
                context=context,
                question=question_for_rag,
            )

        logger.debug(f"  Prompt enriquecido ({len(enriched_prompt)} chars)")

        # ── 8. Enriquecer system prompt con perfil del usuario ─────
        enriched_system_prompt: str = build_enriched_system_prompt(
            RAG_SYSTEM_PROMPT)

        # ── 9. Consultar LLM con historial ──────────────────────────
        answer: str = query_llm_with_history(
            enriched_prompt,
            history=history,
            system_prompt=enriched_system_prompt,
            temperature=0.3,  # Más determinista para RAG
        )

        # ── 10. Resetear sesión adversaria si se proporcionó contexto ──
        if should_reset_adversary:
            self.adversary_session.reset()
            logger.info(
                "Sesión adversaria finalizada después de proporcionar contexto")

        # ── 11. Guardar turno en memoria ────────────────────────────
        self.memory.add_user_message(pregunta)
        self.memory.add_assistant_message(answer)

        # ── 12. Empaquetar respuesta ───────────────────────────────
        sources: List[RetrievedChunk] = [
            RetrievedChunk(**chunk) for chunk in chunks
        ]

        response = RAGResponse(
            answer=answer,
            sources=sources,
            had_context=True,
            query=question_for_rag if (
                use_adversary and should_reset_adversary) else pregunta,
            n_chunks_retrieved=len(sources),
            question_type=detected_question_type,
            adversary_activated=adversary_activated,
            adversary_depth=adversary_depth if adversary_activated else None,
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

            # Mostrar metadata de la respuesta
            metadata_parts = []
            if resp.question_type:
                metadata_parts.append(f"Tipo: {resp.question_type.value}")
            if resp.adversary_activated:
                metadata_parts.append("Adversario: ACTIVO")
                if resp.adversary_depth is not None:
                    metadata_parts.append(f"Profundidad: {resp.adversary_depth}/5")
            else:
                metadata_parts.append("Adversario: INACTIVO")

            if metadata_parts:
                print(f"\n  [{' | '.join(metadata_parts)}]")

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
