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


# ─── Modelos para Plan de Estudio Progresivo ──────────────────────────────

ActionType = Literal["read", "practice", "watch", "project", "review"]


class StudyAction(BaseModel):
    """Acción concreta dentro de una fase."""

    id: str = Field(..., min_length=1, description="Identificador único de la acción")
    type: ActionType = Field(..., description="Tipo de acción")
    description: str = Field(..., min_length=1, description="Descripción de la acción")
    resource: Optional[str] = Field(
        default=None, description="Recurso específico si está disponible (libro, video, ejercicio)"
    )
    estimated_hours: Optional[float] = Field(
        default=None, ge=0, description="Horas estimadas para esta acción"
    )


MilestoneType = Literal["knowledge_check", "practical_exercise", "project", "self_assessment"]


class Milestone(BaseModel):
    """Criterio de superación (hito) para una fase."""

    id: str = Field(..., min_length=1, description="Identificador único del hito")
    description: str = Field(..., min_length=1, description="Descripción del criterio")
    type: MilestoneType = Field(..., description="Tipo de validación")
    validation_hint: Optional[str] = Field(
        default=None, description="Pista sobre cómo validar (ej: 'Resolver 5 ejercicios sin ayuda')"
    )


class StudyPhase(BaseModel):
    """Fase del plan de estudio."""

    id: str = Field(..., min_length=1, description="Identificador único de la fase")
    level: int = Field(..., ge=0, description="Nivel de la fase (0 = fundamentos, último = objetivo)")
    title: str = Field(..., min_length=1, description="Título de la fase")
    description: str = Field(..., min_length=1, description="Descripción de qué se aprende en esta fase")
    concepts: List[str] = Field(default_factory=list, description="Conceptos que se cubren en esta fase")
    prerequisites: List[str] = Field(
        default_factory=list, description="IDs de fases anteriores requeridas"
    )
    actions: List[StudyAction] = Field(default_factory=list, description="Acciones concretas a realizar")
    milestones: List[Milestone] = Field(default_factory=list, description="Criterios de superación")
    estimated_weeks: float = Field(..., ge=0, description="Semanas estimadas para completar esta fase")
    estimated_hours: float = Field(..., ge=0, description="Horas totales estimadas")


class StudyPlanResult(BaseModel):
    """Resultado completo del plan de estudio progresivo."""

    goal: str = Field(..., min_length=1, description="Objetivo del plan")
    inferred_level: str = Field(..., description="Nivel inferido del usuario")
    total_estimated_weeks: float = Field(..., ge=0, description="Total de semanas estimadas")
    total_estimated_hours: float = Field(..., ge=0, description="Total de horas estimadas")
    phases: List[StudyPhase] = Field(default_factory=list, description="Fases ordenadas del plan")


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


STUDY_PLAN_SYSTEM_PROMPT = """Eres un tutor experto que diseña planes de estudio progresivos para temas de matemáticas, física y ciencia de datos.
Cuando el usuario menciona un tema objetivo (ej: "redes neuronales", "cálculo diferencial", "álgebra lineal"), debes diseñar un plan completo desde las bases matemáticas y conceptuales necesarias hasta alcanzar ese objetivo.

Tu respuesta debe ser ÚNICAMENTE un objeto JSON válido, sin texto adicional ni markdown, con esta estructura exacta:

{
  "goal": "redes neuronales",
  "inferred_level": "principiante",
  "total_estimated_weeks": 12.0,
  "total_estimated_hours": 120.0,
  "phases": [
    {
      "id": "phase_1",
      "level": 0,
      "title": "Fundamentos de Álgebra Lineal",
      "description": "Aprender los conceptos básicos de vectores, matrices y operaciones lineales necesarios para entender redes neuronales",
      "concepts": ["vectores", "matrices", "multiplicación de matrices", "transposición"],
      "prerequisites": [],
      "actions": [
        {
          "id": "action_1_1",
          "type": "read",
          "description": "Leer capítulo 1 sobre vectores y matrices del libro de álgebra lineal",
          "resource": "Libro: 'Álgebra Lineal' - Capítulo 1",
          "estimated_hours": 4.0
        },
        {
          "id": "action_1_2",
          "type": "practice",
          "description": "Resolver ejercicios de multiplicación de matrices",
          "resource": "Ejercicios 1-20 de la sección 1.3",
          "estimated_hours": 6.0
        }
      ],
      "milestones": [
        {
          "id": "milestone_1_1",
          "description": "Ser capaz de multiplicar matrices de cualquier tamaño sin errores",
          "type": "practical_exercise",
          "validation_hint": "Resolver 10 ejercicios de multiplicación de matrices sin ayuda"
        }
      ],
      "estimated_weeks": 2.0,
      "estimated_hours": 10.0
    }
  ]
}

Reglas CRÍTICAS para diseñar el plan:

1. IDENTIFICAR EL OBJETIVO:
   - Extrae el tema objetivo del texto del usuario (ej: "redes neuronales", "cálculo diferencial")
   - Si el texto es solo el nombre del tema sin contexto, ese es el objetivo

2. INFERIR NIVEL INICIAL:
   - Si solo menciona el nombre del tema sin conceptos avanzados → "principiante"
   - Si menciona conceptos intermedios o aplicaciones → "intermedio"
   - Si menciona conceptos avanzados, implementaciones o investigación → "avanzado"
   - El campo "inferred_level" debe ser exactamente uno de: "principiante", "intermedio", "avanzado"

3. CONSTRUIR CAMINO PROGRESIVO:
   - Diseña fases ordenadas desde las bases hasta el objetivo
   - Cada fase debe tener un "level" (0 = fundamentos, números mayores = más avanzado)
   - La última fase debe alcanzar el objetivo mencionado
   - Cada fase debe tener "prerequisites" que apunten a IDs de fases anteriores (fase nivel 0 no tiene prerequisitos)
   - Mínimo 3 fases, idealmente entre 4 y 8 fases

4. ACCIONES CONCRETAS:
   - Cada fase debe tener al menos 2-4 acciones
   - Tipos de acción: "read" (leer), "practice" (practicar), "watch" (ver video), "project" (proyecto), "review" (repasar)
   - Incluye acciones genéricas (ej: "Estudiar derivadas") y específicas cuando sea posible (ej: "Leer capítulo 3 del libro X")
   - Estima horas realistas para cada acción

5. CRITERIOS DE SUPERACIÓN (MILESTONES):
   - Cada fase debe tener al menos 1-2 hitos
   - Tipos: "knowledge_check" (verificación de conocimiento), "practical_exercise" (ejercicio práctico), "project" (proyecto), "self_assessment" (autoevaluación)
   - Los hitos deben ser objetivos y medibles
   - Incluye "validation_hint" con pistas sobre cómo validar

6. ESTIMACIONES DE TIEMPO:
   - "estimated_weeks": semanas realistas para completar la fase (considera 5-10 horas por semana)
   - "estimated_hours": suma de horas de todas las acciones de la fase
   - "total_estimated_weeks" y "total_estimated_hours": suma de todas las fases

7. VALIDACIÓN:
   - Todos los IDs de fases en "prerequisites" deben existir en la lista de "phases"
   - Las fases deben estar ordenadas por "level" (0, 1, 2, ...)
   - La fase con mayor "level" debe ser la que alcanza el objetivo

Responde solo con el JSON, sin explicaciones ni ```json."""


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


# ─── Clase para Plan de Estudio Progresivo ─────────────────────────────────


class StudyPlanGenerator:
    """
    Genera un plan de estudio progresivo completo desde las bases hasta un objetivo usando el LLM.

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

    def generate(self, text: str, user_level: Optional[str] = None) -> StudyPlanResult:
        """
        Genera un plan de estudio progresivo desde las bases hasta el objetivo mencionado.

        Args:
            text: Texto con el objetivo del plan (ej: "redes neuronales", "cálculo diferencial").
            user_level: Nivel del usuario ("principiante", "intermedio", "avanzado").
                Si es None, se infiere del texto.

        Returns:
            StudyPlanResult con fases ordenadas, acciones, hitos y estimaciones de tiempo.

        Raises:
            ValueError: Si text está vacío, el JSON no es válido/validable,
                        o hay prerequisitos que no existen en las fases.
        """
        if not text.strip():
            raise ValueError("El texto no puede estar vacío.")

        text_stripped = text.strip()

        # Construir prompt con nivel explícito o instrucción para inferir
        if user_level:
            level_instruction = f"El usuario tiene nivel '{user_level}'. Diseña el plan apropiado para este nivel."
        else:
            level_instruction = "Infiere el nivel inicial del usuario basándote en el texto proporcionado."

        user_prompt = f"""Diseña un plan de estudio progresivo completo para alcanzar el siguiente objetivo.
{level_instruction}

Objetivo mencionado por el usuario:
---
{text_stripped}
---

Responde solo con el JSON siguiendo la estructura especificada."""

        raw_response: str = self._llm(
            user_prompt,
            system_prompt=STUDY_PLAN_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=4096,  # Más tokens para planes más complejos
        )

        json_str = _extract_json_from_response(raw_response)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"La respuesta del LLM no es JSON válido: {e}") from e

        # Validar estructura básica
        if "phases" not in data:
            raise ValueError("La respuesta del LLM no contiene 'phases'")

        phases_data = data.get("phases") or []
        if not phases_data:
            raise ValueError("El plan debe tener al menos una fase")

        # Validar y crear fases
        phases = [StudyPhase.model_validate(p) for p in phases_data]

        # Validar prerequisitos
        phase_ids = {p.id for p in phases}
        for phase in phases:
            for prereq_id in phase.prerequisites:
                if prereq_id not in phase_ids:
                    raise ValueError(
                        f"La fase '{phase.id}' tiene un prerequisito '{prereq_id}' que no existe en las fases"
                    )

        # Validar orden: fase nivel 0 no debe tener prerequisitos
        level_0_phases = [p for p in phases if p.level == 0]
        for phase in level_0_phases:
            if phase.prerequisites:
                raise ValueError(
                    f"La fase '{phase.id}' tiene nivel 0 pero tiene prerequisitos. Las fases nivel 0 no deben tener prerequisitos."
                )

        # Ordenar fases por nivel
        phases_sorted = sorted(phases, key=lambda p: p.level)

        # Validar que inferred_level sea válido
        inferred_level = data.get("inferred_level", "principiante")
        if inferred_level not in ["principiante", "intermedio", "avanzado"]:
            inferred_level = "principiante"

        # Calcular totales si no están presentes o validar si están
        total_weeks = data.get("total_estimated_weeks")
        total_hours = data.get("total_estimated_hours")
        if total_weeks is None:
            total_weeks = sum(p.estimated_weeks for p in phases_sorted)
        if total_hours is None:
            total_hours = sum(p.estimated_hours for p in phases_sorted)

        goal = data.get("goal", text_stripped)

        return StudyPlanResult(
            goal=goal,
            inferred_level=inferred_level,
            total_estimated_weeks=float(total_weeks),
            total_estimated_hours=float(total_hours),
            phases=phases_sorted,
        )
