"""
Mapas Mentales Semánticos — Generación de grafos de conocimiento desde texto

Transforma texto no estructurado (documentos, apuntes) en un grafo de nodos y aristas
que representan conceptos y sus relaciones, para visualización interactiva (ReactFlow).

Componentes:
    - Node, Edge: modelos Pydantic estrictos para nodos y relaciones.
    - MindMapResult: resultado completo (nodes + edges + metadata opcional).
    - MindMapGenerator: clase que usa el LLM para extraer el grafo desde el texto.

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import json
import re
from typing import Any, Callable, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from src.brain.llm_client import query_llm

# ─── Modelos Pydantic ────────────────────────────────────────

NodeType = Literal["concept", "topic", "detail"]


class Node(BaseModel):
    """Nodo del mapa mental: concepto, tema o detalle."""

    id: str = Field(..., min_length=1, description="Identificador único del nodo")
    label: str = Field(..., min_length=1, description="Texto mostrado (concepto o tema)")
    type: NodeType = Field(
        ...,
        description="Tipo del nodo: concept, topic o detail",
    )

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, v: Any) -> str:
        if isinstance(v, str):
            v = v.strip().lower()
        return v


class Edge(BaseModel):
    """Arista del mapa mental: relación entre dos nodos."""

    source: str = Field(..., min_length=1, description="Id del nodo origen")
    target: str = Field(..., min_length=1, description="Id del nodo destino")
    relation: str = Field(..., min_length=1, description="Descripción breve de la relación")


class MindMapResult(BaseModel):
    """Resultado de la generación del mapa mental."""

    nodes: List[Node] = Field(default_factory=list, description="Lista de nodos")
    edges: List[Edge] = Field(default_factory=list, description="Lista de aristas")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Trazabilidad opcional")


# ─── Prompt del sistema ───────────────────────────────────────

MINDMAP_SYSTEM_PROMPT = """Eres un asistente que extrae conceptos clave y sus relaciones de un texto académico.
Tu respuesta debe ser ÚNICAMENTE un objeto JSON válido, sin texto adicional ni markdown, con esta estructura exacta:

{
  "nodes": [
    { "id": "n1", "label": "Nombre del concepto", "type": "concept" },
    { "id": "n2", "label": "Otro concepto", "type": "topic" }
  ],
  "edges": [
    { "source": "n1", "target": "n2", "relation": "descripción breve de la relación" }
  ]
}

Reglas:
- "id" de cada nodo: string único (ej. n1, n2, n3). Usa los mismos ids en "source" y "target" de edges.
- "type" de cada nodo debe ser exactamente uno de: "concept", "topic", "detail".
- Mínimo 3 nodos y mínimo 2 aristas. Objetivo: entre 5 y 20 nodos con varias relaciones para formar un grafo útil.
- Si el texto es muy breve (una palabra, sigla o frase corta como "ML", "Cálculo", "Integrales"): interpreta ese término como tema central y añade 5-12 conceptos o subtemas relacionados de ese dominio, con aristas que los conecten (ej. "ML" -> Aprendizaje supervisado, No supervisado, Regresión, Clasificación, Redes neuronales, etc.).
- Las "relation" deben ser frases cortas en español (ej. "se fundamenta en", "es un caso de", "incluye", "requiere").
- Responde solo con el JSON, sin explicaciones ni ```json."""


def _extract_json_from_response(raw: str) -> str:
    """Extrae el primer objeto JSON del texto (por si el LLM envuelve en markdown)."""
    raw = raw.strip()
    # Quitar bloques ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if match:
        return match.group(1).strip()
    # Buscar primer { hasta el último } balanceado
    start = raw.find("{")
    if start == -1:
        return raw
    depth = 0
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]
    return raw[start:]


# ─── Clase principal ──────────────────────────────────────────

class MindMapGenerator:
    """
    Genera un mapa mental (grafo de conocimiento) a partir de texto usando el LLM.

    Por defecto usa query_llm de llm_client. Se puede inyectar otro callable
    para pruebas o uso con response_format (OpenAI JSON mode).
    """

    def __init__(
        self,
        llm_callable: Optional[Callable[..., str]] = None,
    ) -> None:
        """
        Args:
            llm_callable: Función (pregunta, *, system_prompt=...) -> str.
                Si es None, se usa query_llm de src.brain.llm_client.
        """
        self._llm = llm_callable if llm_callable is not None else query_llm

    def generate(self, text: str) -> MindMapResult:
        """
        Extrae nodos y aristas del texto y devuelve un MindMapResult validado.

        Args:
            text: Texto del documento o fragmento (no vacío).

        Returns:
            MindMapResult con nodes, edges y metadata opcional.

        Raises:
            ValueError: Si text está vacío o el JSON no es válido/validable.
        """
        if not text.strip():
            raise ValueError("El texto no puede estar vacío.")

        text_stripped = text.strip()
        is_short = len(text_stripped.split()) <= 3 or len(text_stripped) < 50
        extra = (
            " (El texto es breve: expande este término en 5-12 conceptos o subtemas relacionados y conéctalos con aristas.)"
            if is_short
            else ""
        )
        user_prompt = f"Extrae los conceptos clave y sus relaciones del siguiente texto.{extra} Responde solo con el JSON.\n\n---\n\n{text_stripped}"

        raw_response: str = self._llm(
            user_prompt,
            system_prompt=MINDMAP_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=2048,
        )

        json_str = _extract_json_from_response(raw_response)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"La respuesta del LLM no es JSON válido: {e}") from e

        nodes_data = data.get("nodes") or []
        edges_data = data.get("edges") or []

        nodes = [Node.model_validate(n) for n in nodes_data]
        edges = [Edge.model_validate(e) for e in edges_data]

        # Validar que source/target existan en nodes
        node_ids = {n.id for n in nodes}
        for e in edges:
            if e.source not in node_ids:
                raise ValueError(f"Edge source '{e.source}' no existe en nodes")
            if e.target not in node_ids:
                raise ValueError(f"Edge target '{e.target}' no existe en nodes")

        metadata: Optional[Dict[str, Any]] = {
            "source_text_length": len(text),
        }

        return MindMapResult(nodes=nodes, edges=edges, metadata=metadata)
