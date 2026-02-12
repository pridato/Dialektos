"""
El Adversario — Sistema Socrático de Cuestionamiento

Implementa un sistema de prompt engineering que actúa como "adversario socrático",
cuestionando al usuario y pidiendo justificaciones en lugar de dar respuestas
directas. Fomenta el aprendizaje activo mediante el método socrático.

Componentes:
    - QuestionType: Enum para clasificar tipos de pregunta
    - AdversaryState: Estado de la sesión adversaria
    - QuestionAnalyzer: Analiza y clasifica preguntas usando LLM
    - AdversaryPromptBuilder: Construye prompts socráticos
    - AdversarySession: Gestiona el flujo completo del modo adversario

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import logging
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from src.brain.llm_client import query_llm, query_llm_with_history
from src.brain.user_profile import build_enriched_system_prompt

logger = logging.getLogger(__name__)


# ─── Tipos de Pregunta ──────────────────────────────────────────

class QuestionType(str, Enum):
    """
    Tipos de pregunta/afirmación detectables por el sistema.

    Attributes:
        CONCEPTUAL: Requiere comprensión profunda del "por qué" o relaciones
            entre conceptos (ej: "¿Por qué funciona el gradiente descendente?")
        FACTUAL: Pregunta sobre definiciones, fórmulas, o datos concretos
            (ej: "¿Qué es una derivada?")
        PROCEDURAL: Pregunta sobre cómo hacer algo paso a paso
            (ej: "¿Cómo calculo la integral de x²?")
        ASSERTION: Afirmación/declaración que parece conocimiento pero puede
            ser una simplificación peligrosa. Estas son las más peligrosas porque
            el estudiante puede pensar que ya entiende cuando en realidad tiene
            una comprensión superficial o incorrecta.
            (ej: "Los embeddings son representaciones de texto en espacios vectoriales",
             "La regresión lineal siempre funciona bien", "El overfitting es malo")
    """

    CONCEPTUAL = "CONCEPTUAL"
    FACTUAL = "FACTUAL"
    PROCEDURAL = "PROCEDURAL"
    ASSERTION = "ASSERTION"


# ─── Prompts Especializados ──────────────────────────────────────

QUESTION_ANALYZER_PROMPT: str = (
    "Analiza esta entrada del usuario y clasifícala como:\n"
    "- CONCEPTUAL: Pregunta que requiere comprensión profunda del 'por qué' o relaciones "
    "entre conceptos (ej: '¿Por qué funciona X?', '¿Cuál es la relación entre A y B?')\n"
    "- FACTUAL: Pregunta sobre definiciones, fórmulas, o datos concretos "
    "(ej: '¿Qué es X?', '¿Cuál es la fórmula de Y?')\n"
    "- PROCEDURAL: Pregunta sobre cómo hacer algo paso a paso "
    "(ej: '¿Cómo calculo X?', '¿Cuál es el algoritmo para Y?')\n"
    "- ASSERTION: Afirmación o declaración que parece conocimiento pero puede ser "
    "una simplificación peligrosa. Detecta cuando el usuario hace una afirmación "
    "directa sin preguntar (ej: 'Los embeddings son representaciones de texto', "
    "'La regresión lineal siempre funciona', 'El overfitting es malo', "
    "'Los espacios vectoriales tienen dimensión finita'). "
    "Estas son las MÁS PELIGROSAS porque el estudiante puede pensar que entiende "
    "cuando en realidad tiene comprensión superficial.\n\n"
    "Responde SOLO con una palabra: CONCEPTUAL, FACTUAL, PROCEDURAL, o ASSERTION."
)

ADVERSARY_SYSTEM_PROMPT: str = (
    "Eres Dialektos en modo 'El Adversario'. Tu objetivo NO es responder "
    "directamente, sino cuestionar al estudiante usando el método socrático "
    "para que llegue a la comprensión por sí mismo.\n\n"
    "REGLAS ESTRICTAS:\n"
    "1. NUNCA des la respuesta directa. En su lugar, haz una pregunta que "
    "guíe al pensamiento.\n"
    "2. Si el estudiante da una respuesta parcialmente correcta, cuestiona "
    "los aspectos débiles o incompletos.\n"
    "3. Si el estudiante demuestra comprensión profunda (menciona conceptos "
    "clave, relaciones, aplicaciones), entonces confirma y proporciona contexto "
    "adicional de los apuntes.\n"
    "4. Mantén un tono pedagógico pero desafiante. No seas condescendiente.\n"
    "5. Usa analogías cuando sea apropiado para guiar el pensamiento.\n"
    "6. Si el estudiante pide explícitamente la respuesta o parece frustrado, "
    "puedes proporcionar más guía, pero siempre intenta que llegue a la "
    "conclusión por sí mismo primero."
)

ASSERTION_CHALLENGER_PROMPT: str = (
    "Eres Dialektos en modo 'El Adversario' enfrentando una AFIRMACIÓN del estudiante. "
    "Las afirmaciones son las MÁS PELIGROSAS porque el estudiante puede pensar que "
    "ya entiende cuando en realidad tiene una comprensión superficial o incorrecta.\n\n"
    "Tu misión es ROMPER la afirmación para llevarlo a un nuevo nivel de conocimiento:\n\n"
    "ESTRATEGIAS DE CUESTIONAMIENTO:\n"
    "1. Busca las simplificaciones ocultas: '¿Siempre es así?', '¿En qué casos NO se cumple?'\n"
    "2. Expone los matices faltantes: '¿Qué matices tiene esa afirmación?', "
    "'¿Qué condiciones faltan?'\n"
    "3. Cuestiona las asunciones implícitas: '¿Qué asumes cuando dices eso?', "
    "'¿Qué condiciones no mencionaste?'\n"
    "4. Busca contraejemplos: '¿Puedes pensar en un caso donde eso no se cumpla?', "
    "'¿Qué excepciones conoces?'\n"
    "5. Profundiza en las relaciones: '¿Cómo se relaciona eso con X?', "
    "'¿Qué implicaciones tiene esa afirmación?'\n"
    "6. Cuestiona el nivel de generalidad: '¿Eso es siempre cierto o solo en ciertos contextos?', "
    "'¿Qué limitaciones tiene?'\n\n"
    "OBJETIVO: No destruir su confianza, sino mostrarle que el conocimiento real "
    "es más rico y matizado de lo que pensaba. Guíalo a descubrir las excepciones, "
    "condiciones y matices que hacen que su afirmación sea parcialmente correcta "
    "pero incompleta.\n\n"
    "TONO: Desafiante pero constructivo. No digas 'estás equivocado', sino "
    "'exploremos los matices de esa afirmación'."
)

COMPREHENSION_EVALUATOR_PROMPT: str = (
    "Evalúa si la respuesta del estudiante demuestra comprensión suficiente "
    "del concepto que se está explorando.\n\n"
    "Indicadores de comprensión:\n"
    "- Menciona conceptos clave relacionados\n"
    "- Explica relaciones o causas\n"
    "- Proporciona ejemplos o analogías\n"
    "- Muestra conexión con otros conceptos\n"
    "- Demuestra razonamiento lógico\n\n"
    "Responde SOLO con 'SI' si demuestra comprensión suficiente, o 'NO' si "
    "la respuesta es superficial, incorrecta, o solo repite información sin "
    "demostrar entendimiento profundo."
)


# ─── Modelos Pydantic ────────────────────────────────────────────

class AdversaryState(BaseModel):
    """
    Estado de la sesión adversaria.

    Mantiene el contexto de una conversación en modo adversario, incluyendo
    la profundidad del cuestionamiento y las respuestas del usuario.

    Attributes:
        is_active: Si el modo adversario está activo en este momento.
        question_depth: Profundidad de cuestionamiento actual (1-5).
        user_responses: Lista de respuestas del usuario en esta sesión.
        concept_being_explored: Concepto principal que se está explorando.
        original_question: Pregunta original que activó el modo adversario.
    """

    is_active: bool = False
    question_depth: int = Field(default=0, ge=0, le=5)
    user_responses: List[str] = Field(default_factory=list)
    concept_being_explored: str = ""
    original_question: str = ""

    def reset(self) -> None:
        """Reinicia el estado a valores iniciales."""
        self.is_active = False
        self.question_depth = 0
        self.user_responses.clear()
        self.concept_being_explored = ""
        self.original_question = ""


# ─── Clases Principales ──────────────────────────────────────────

class QuestionAnalyzer:
    """
    Analiza y clasifica preguntas usando un LLM.

    Determina si una pregunta requiere comprensión conceptual profunda
    (activando el modo adversario) o puede responderse directamente con RAG.
    """

    @staticmethod
    def analyze_question(pregunta: str) -> QuestionType:
        """
        Clasifica el tipo de pregunta usando un LLM.

        Args:
            pregunta: La pregunta del usuario a analizar.

        Returns:
            QuestionType indicando si es CONCEPTUAL, FACTUAL o PROCEDURAL.

        Raises:
            ValueError: Si el LLM retorna un tipo no reconocido.
        """
        try:
            response: str = query_llm(
                pregunta=f"Pregunta: {pregunta}\n\n{QUESTION_ANALYZER_PROMPT}",
                system_prompt="Eres un analizador de intenciones educativas.",
                temperature=0.0,  # Determinista para clasificación
                max_tokens=10,
            )

            # Limpiar respuesta (eliminar espacios, mayúsculas/minúsculas)
            response_clean: str = response.strip().upper()

            # Buscar el tipo en la respuesta
            for qtype in QuestionType:
                if qtype.value in response_clean:
                    logger.info(f"Pregunta clasificada como: {qtype.value}")
                    return qtype

            # Fallback: si no se encuentra, asumir CONCEPTUAL por seguridad
            logger.warning(
                f"Tipo de pregunta no reconocido: '{response}'. "
                "Asumiendo CONCEPTUAL."
            )
            return QuestionType.CONCEPTUAL

        except Exception as e:
            logger.error(f"Error al analizar pregunta: {e}. Asumiendo CONCEPTUAL.")
            return QuestionType.CONCEPTUAL


class AdversaryPromptBuilder:
    """
    Construye prompts socráticos para el modo adversario.

    Genera prompts que fuerzan al LLM a cuestionar en lugar de responder
    directamente, adaptándose al estado de la sesión.
    """

    @staticmethod
    def build_adversary_prompt(
        question: str,
        state: AdversaryState,
        context: Optional[str] = None,
        question_type: Optional[QuestionType] = None,
    ) -> str:
        """
        Construye un prompt para generar una pregunta socrática.

        Args:
            question: La pregunta o afirmación original del usuario o su última respuesta.
            state: Estado actual de la sesión adversaria.
            context: Contexto opcional de los apuntes (solo después de
                que el usuario demuestre comprensión).
            question_type: Tipo de entrada (CONCEPTUAL o ASSERTION).

        Returns:
            Prompt formateado para el LLM en modo adversario.
        """
        # Detectar si es una afirmación
        is_assertion: bool = question_type == QuestionType.ASSERTION

        if is_assertion:
            base_prompt = (
                f"El estudiante hizo esta AFIRMACIÓN: '{state.original_question}'\n\n"
                if state.original_question
                else f"El estudiante hizo esta AFIRMACIÓN: '{question}'\n\n"
            )
        else:
            base_prompt = (
                f"El estudiante pregunta: '{state.original_question}'\n\n"
                if state.original_question
                else ""
            )

        if state.user_responses:
            base_prompt += "Respuestas previas del estudiante:\n"
            for i, resp in enumerate(state.user_responses, 1):
                base_prompt += f"{i}. {resp}\n"
            base_prompt += "\n"

        if context:
            base_prompt += (
                "--- CONTEXTO DE LOS APUNTES ---\n"
                f"{context}\n"
                "--- FIN CONTEXTO ---\n\n"
            )

        if state.question_depth == 0:
            if is_assertion:
                base_prompt += (
                    f"Esta afirmación parece conocimiento pero puede ser una simplificación "
                    f"peligrosa. ROMPE la afirmación usando las estrategias de cuestionamiento:\n"
                    f"- Busca simplificaciones ocultas\n"
                    f"- Expone matices faltantes\n"
                    f"- Cuestiona asunciones implícitas\n"
                    f"- Busca contraejemplos\n"
                    f"- Profundiza en las relaciones\n"
                    f"- Cuestiona el nivel de generalidad\n\n"
                    f"Genera una pregunta que desafíe esta afirmación y guíe al estudiante "
                    f"a descubrir los matices, excepciones y condiciones que hacen que su "
                    f"afirmación sea parcialmente correcta pero incompleta."
                )
            else:
                base_prompt += (
                    f"Genera una pregunta socrática que guíe al estudiante hacia "
                    f"la comprensión de: '{question}'. "
                    "NO des la respuesta directa."
                )
        else:
            if is_assertion:
                base_prompt += (
                    f"El estudiante ha respondido parcialmente a tu cuestionamiento. "
                    f"Profundiza con una pregunta más específica (nivel {state.question_depth + 1}/5). "
                    f"Sigue rompiendo la afirmación original: busca más matices, excepciones, "
                    f"o condiciones que el estudiante aún no ha considerado."
                )
            else:
                base_prompt += (
                    f"El estudiante ha respondido parcialmente. Profundiza con "
                    f"una pregunta más específica (nivel {state.question_depth + 1}/5). "
                    "Cuestiona aspectos que aún no ha explorado o conexiones que "
                    "no ha hecho."
                )

        return base_prompt


class AdversarySession:
    """
    Gestiona el flujo completo del modo adversario.

    Coordina el análisis de preguntas, generación de preguntas socráticas,
    evaluación de comprensión y decisión de cuándo proporcionar contexto RAG.
    """

    def __init__(self, max_depth: int = 5) -> None:
        """
        Inicializa una sesión adversaria.

        Args:
            max_depth: Profundidad máxima de cuestionamiento antes de
                proporcionar contexto (default: 5).
        """
        self.state: AdversaryState = AdversaryState()
        self.max_depth: int = max_depth
        self.analyzer: QuestionAnalyzer = QuestionAnalyzer()
        self.prompt_builder: AdversaryPromptBuilder = AdversaryPromptBuilder()

    def should_activate(self, pregunta: str) -> bool:
        """
        Determina si se debe activar el modo adversario para una entrada del usuario.

        Analiza el tipo de entrada y activa el modo adversario para:
        - Preguntas conceptuales (requieren comprensión profunda)
        - Afirmaciones/declaraciones (las más peligrosas: parecen conocimiento pero
          pueden ser simplificaciones que ocultan malentendidos)

        Args:
            pregunta: La pregunta o afirmación del usuario.

        Returns:
            True si se debe activar el modo adversario, False en caso contrario.
        """
        question_type: QuestionType = self.analyzer.analyze_question(pregunta)

        if question_type == QuestionType.CONCEPTUAL:
            logger.info("Activando modo adversario para pregunta conceptual")
            self.state.is_active = True
            self.state.original_question = pregunta
            self.state.concept_being_explored = pregunta
            return True

        if question_type == QuestionType.ASSERTION:
            logger.info(
                "⚠️  Activando modo adversario para AFIRMACIÓN peligrosa "
                "(simplificación que puede ocultar malentendidos)"
            )
            self.state.is_active = True
            self.state.original_question = pregunta
            self.state.concept_being_explored = pregunta
            return True

        logger.info(f"Modo adversario NO activado (tipo: {question_type.value})")
        return False

    def generate_socratic_question(
        self,
        pregunta: str,
        context: Optional[str] = None,
    ) -> str:
        """
        Genera una pregunta socrática usando el LLM.

        Args:
            pregunta: La pregunta o afirmación original o la última respuesta del usuario.
            context: Contexto opcional de los apuntes (solo si el usuario
                ya demostró comprensión).

        Returns:
            Pregunta socrática generada por el LLM.
        """
        # Detectar el tipo de entrada para usar el prompt adecuado
        question_type: QuestionType = self.analyzer.analyze_question(
            self.state.original_question or pregunta
        )

        prompt: str = self.prompt_builder.build_adversary_prompt(
            question=pregunta,
            state=self.state,
            context=context,
            question_type=question_type,
        )

        # Usar prompt especializado para afirmaciones
        if question_type == QuestionType.ASSERTION:
            system_prompt: str = build_enriched_system_prompt(ASSERTION_CHALLENGER_PROMPT)
        else:
            system_prompt: str = build_enriched_system_prompt(ADVERSARY_SYSTEM_PROMPT)

        try:
            socratic_question: str = query_llm(
                pregunta=prompt,
                system_prompt=system_prompt,
                temperature=0.7,  # Más creativo para preguntas socráticas
                max_tokens=250,  # Un poco más para afirmaciones complejas
            )

            question_type_label: str = (
                "afirmación peligrosa" if question_type == QuestionType.ASSERTION
                else "pregunta conceptual"
            )
            logger.info(
                f"Pregunta socrática generada para {question_type_label} "
                f"(profundidad: {self.state.question_depth + 1})"
            )
            return socratic_question.strip()

        except Exception as e:
            logger.error(f"Error al generar pregunta socrática: {e}")
            if question_type == QuestionType.ASSERTION:
                return (
                    "Interesante afirmación. Antes de aceptarla completamente, "
                    "¿en qué casos o condiciones podría no cumplirse? "
                    "¿Qué matices o excepciones podrías estar pasando por alto?"
                )
            return (
                "Antes de responder directamente, ¿qué aspectos fundamentales "
                "de este concepto crees que son importantes de entender?"
            )

    def evaluate_user_response(self, respuesta_usuario: str) -> bool:
        """
        Evalúa si la respuesta del usuario demuestra comprensión suficiente.

        Usa un LLM auxiliar para determinar si la respuesta muestra
        comprensión profunda o es superficial.

        Args:
            respuesta_usuario: La respuesta del usuario a evaluar.

        Returns:
            True si demuestra comprensión suficiente, False en caso contrario.
        """
        if not self.state.original_question:
            return False

        evaluation_prompt = (
            f"Pregunta original: {self.state.original_question}\n"
            f"Respuesta del estudiante: {respuesta_usuario}\n\n"
            f"{COMPREHENSION_EVALUATOR_PROMPT}"
        )

        try:
            evaluation: str = query_llm(
                pregunta=evaluation_prompt,
                system_prompt="Eres un evaluador de comprensión educativa.",
                temperature=0.0,
                max_tokens=5,
            )

            evaluation_clean: str = evaluation.strip().upper()
            demonstrates_comprehension: bool = "SI" in evaluation_clean

            logger.info(
                f"Evaluación de comprensión: {'SUFICIENTE' if demonstrates_comprehension else 'INSUFICIENTE'}"
            )

            return demonstrates_comprehension

        except Exception as e:
            logger.error(f"Error al evaluar comprensión: {e}")
            # En caso de error, asumir comprensión insuficiente para continuar cuestionando
            return False

    def add_user_response(self, respuesta: str) -> None:
        """
        Registra una respuesta del usuario y actualiza el estado.

        Args:
            respuesta: La respuesta del usuario.
        """
        self.state.user_responses.append(respuesta)
        self.state.question_depth += 1

    def should_provide_context(self) -> bool:
        """
        Determina si se debe proporcionar contexto RAG al usuario.

        Se proporciona contexto cuando:
        - El usuario demuestra comprensión suficiente, O
        - Se alcanza la profundidad máxima de cuestionamiento.

        Returns:
            True si se debe proporcionar contexto, False en caso contrario.
        """
        return (
            self.state.question_depth >= self.max_depth
            or (
                self.state.user_responses
                and self.evaluate_user_response(self.state.user_responses[-1])
            )
        )

    def reset(self) -> None:
        """Reinicia la sesión adversaria."""
        self.state.reset()
        logger.info("Sesión adversaria reiniciada")
