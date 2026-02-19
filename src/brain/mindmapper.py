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


# ─── Modelos para Ruta de Estudio Estructurada ──────────────────────────


class StudyPathNode(BaseModel):
    """Nodo de la ruta de estudio con dependencias conceptuales."""

    id: str = Field(..., min_length=1, description="Identificador único del nodo")
    label: str = Field(..., min_length=1, description="Nombre del concepto")
    description: str = Field(..., min_length=1, description="Resumen de 1-2 líneas del concepto")
    difficulty: int = Field(..., ge=1, le=5, description="Dificultad del concepto (1=fácil, 5=muy difícil)")
    prerequisites: List[str] = Field(
        default_factory=list,
        description="Array de ids de otros nodos que deben saberse antes",
    )


class StudyPathResult(BaseModel):
    """Resultado de la generación de la ruta de estudio estructurada."""

    nodes: List[StudyPathNode] = Field(default_factory=list, description="Lista de nodos con dependencias")


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


STUDY_PATH_SYSTEM_PROMPT = """Eres un asistente especializado en análisis lógico de textos académicos de matemáticas y física.
Tu tarea es analizar el texto y extraer conceptos fundamentales y avanzados, identificando sus dependencias conceptuales estrictas.

Tu respuesta debe ser ÚNICAMENTE un objeto JSON válido, sin texto adicional ni markdown, con esta estructura exacta:

{
  "nodes": [
    {
      "id": "c1",
      "label": "Nombre del concepto",
      "description": "Resumen breve de 1-2 líneas explicando qué es este concepto",
      "difficulty": 2,
      "prerequisites": []
    },
    {
      "id": "c2",
      "label": "Otro concepto avanzado",
      "description": "Este concepto requiere entender c1 primero",
      "difficulty": 4,
      "prerequisites": ["c1"]
    }
  ]
}

Reglas CRÍTICAS para crear el grafo de dependencias:
- Analiza el texto desde la lógica matemática/física. Identifica conceptos fundamentales (sin prerequisitos) y conceptos avanzados (con prerequisitos).
- Si el concepto B usa fórmulas, teoremas, definiciones o teoría del concepto A, entonces A DEBE ser un prerrequisito de B.
- Crea un grafo de dependencias ESTRICTO: si B depende de A, entonces "prerequisites" de B debe incluir el "id" de A.
- "id": string único para cada concepto (ej. c1, c2, c3, derivada, integral, limite).
- "label": nombre corto y claro del concepto.
- "description": resumen de 1-2 líneas en español explicando qué es el concepto.
- "difficulty": número entero de 1 (muy fácil) a 5 (muy difícil).
- "prerequisites": array de strings con los "id" de otros nodos que deben saberse antes. Si no hay prerequisitos, usa [].
- Mínimo 5 nodos. Objetivo: entre 8 y 25 conceptos con dependencias claras.
- Asegúrate de que todos los ids en "prerequisites" existan en la lista de "nodes".
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


# ─── Clase para Ruta de Estudio Estructurada ───────────────────────────────


class StudyPathGenerator:
    """
    Genera una ruta de estudio estructurada (DAG de dependencias conceptuales) a partir de texto usando el LLM.

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

    def generate(self, text: str) -> StudyPathResult:
        """
        Extrae nodos con dependencias conceptuales del texto y devuelve un StudyPathResult validado.

        Args:
            text: Texto del documento o fragmento (no vacío).

        Returns:
            StudyPathResult con nodes (cada nodo tiene prerequisites).

        Raises:
            ValueError: Si text está vacío, el JSON no es válido/validable,
                        o hay prerequisitos que no existen en los nodos.
        """
        if not text.strip():
            raise ValueError("El texto no puede estar vacío.")

        text_stripped = text.strip()
        user_prompt = f"Analiza el siguiente texto de matemáticas/física y extrae los conceptos con sus dependencias. Responde solo con el JSON.\n\n---\n\n{text_stripped}"

        raw_response: str = self._llm(
            user_prompt,
            system_prompt=STUDY_PATH_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=2048,
        )

        json_str = _extract_json_from_response(raw_response)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"La respuesta del LLM no es JSON válido: {e}") from e

        nodes_data = data.get("nodes") or []

        nodes = [StudyPathNode.model_validate(n) for n in nodes_data]

        # Validar que todos los prerequisitos existan en los nodos
        node_ids = {n.id for n in nodes}
        for node in nodes:
            for prereq_id in node.prerequisites:
                if prereq_id not in node_ids:
                    raise ValueError(
                        f"El nodo '{node.id}' tiene un prerequisito '{prereq_id}' que no existe en los nodos"
                    )

        return StudyPathResult(nodes=nodes)
