"""
Conversation Memory — Historial de conversación con ventana deslizante

Gestiona el historial de mensajes de una conversación multi-turno,
proporcionando una ventana deslizante configurable para evitar
exceder el límite de tokens del modelo.

Componentes:
    - ChatMessage: modelo Pydantic para un mensaje individual.
    - ConversationMemory: buffer circular de mensajes con ventana
      deslizante por turnos (1 turno = 1 par user + assistant).

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

from typing import Dict, List, Literal

from pydantic import BaseModel, Field


# ─── Modelos Pydantic ────────────────────────────────────────

class ChatMessage(BaseModel):
    """
    Mensaje individual de la conversación.

    Attributes:
        role: Rol del emisor (``"user"`` o ``"assistant"``).
        content: Contenido textual del mensaje.
    """

    role: Literal["user", "assistant"]
    content: str


# ─── Memoria Conversacional ──────────────────────────────────

class ConversationMemory:
    """
    Buffer de historial conversacional con ventana deslizante.

    Almacena mensajes ``user`` / ``assistant`` y los expone como
    lista de dicts compatible con la API de OpenAI.  Al superar
    ``max_turns`` turnos completos (1 turno = 1 par user+assistant),
    los turnos más antiguos se descartan automáticamente.

    Attributes:
        max_turns: Número máximo de turnos a retener (default: 5).

    Example:
        >>> mem = ConversationMemory(max_turns=3)
        >>> mem.add_user_message("¿Qué es un espacio vectorial?")
        >>> mem.add_assistant_message("Un espacio vectorial es ...")
        >>> mem.is_first_turn
        False
        >>> len(mem)
        1
    """

    def __init__(self, max_turns: int = 5) -> None:
        """
        Inicializa la memoria con un límite de turnos.

        Args:
            max_turns: Número máximo de turnos (pares user+assistant)
                a conservar.  Valores menores reducen consumo de tokens
                pero pierden contexto más rápido.
        """
        if max_turns < 1:
            raise ValueError("max_turns debe ser >= 1.")
        self.max_turns: int = max_turns
        self._messages: List[ChatMessage] = []

    # ── Agregar mensajes ─────────────────────────────────────

    def add_user_message(self, content: str) -> None:
        """
        Registra un mensaje del usuario.

        Args:
            content: Texto del mensaje del usuario.
        """
        self._messages.append(ChatMessage(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        """
        Registra un mensaje del asistente y aplica la ventana deslizante.

        La poda se ejecuta aquí porque un turno solo está completo
        cuando el asistente responde.  Tras cada respuesta se verifica
        si se excedió ``max_turns`` y se eliminan los turnos más antiguos.

        Args:
            content: Texto de la respuesta del asistente.
        """
        self._messages.append(ChatMessage(role="assistant", content=content))
        self._trim()

    # ── Consultar historial ──────────────────────────────────

    def get_messages(self) -> List[Dict[str, str]]:
        """
        Devuelve el historial como lista de dicts (compatible con OpenAI).

        Returns:
            Lista de ``{"role": ..., "content": ...}`` ordenada
            cronológicamente.

        Example:
            >>> mem.get_messages()
            [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        return [msg.model_dump() for msg in self._messages]

    @property
    def is_first_turn(self) -> bool:
        """
        True si aún no hay turnos completos en la memoria.

        Se usa para decidir si se necesita query rewriting:
        en el primer turno la pregunta es autocontenida.
        """
        return len(self._messages) == 0

    # ── Utilidades ───────────────────────────────────────────

    def clear(self) -> None:
        """Limpia todo el historial de la conversación."""
        self._messages.clear()

    def __len__(self) -> int:
        """
        Número de turnos completos (pares user+assistant) almacenados.

        Un mensaje ``user`` sin respuesta ``assistant`` no cuenta
        como turno completo.
        """
        return sum(1 for msg in self._messages if msg.role == "assistant")

    def __repr__(self) -> str:
        return (
            f"ConversationMemory(max_turns={self.max_turns}, "
            f"turns={len(self)}, messages={len(self._messages)})"
        )

    # ── Internos ─────────────────────────────────────────────

    def _trim(self) -> None:
        """
        Poda los turnos más antiguos si se excede ``max_turns``.

        Opera sobre pares completos: elimina los 2 mensajes más
        antiguos (user + assistant) por cada turno excedente.
        """
        n_turns: int = len(self)
        if n_turns > self.max_turns:
            excess: int = n_turns - self.max_turns
            # Cada turno son 2 mensajes (user + assistant)
            self._messages = self._messages[excess * 2:]
