"""
Motor de Decisión (Thresholding) — Módulo Bio-Adaptabilidad

Mapea el Índice Cognitivo Diario (ICD) a una estrategia pedagógica concreta,
automatizando la decisión de "qué estudiar hoy" basándose en datos fisiológicos.

Zonas cognitivas:
    - PEAK   (ICD > 80):  Deep Work — temas nuevos, matemáticas, Socrático.
    - NORMAL (ICD 50-80): Flow — programación, ejercicios estándar.
    - FATIGUE (ICD 30-50): Review — repaso espaciado, documentación.
    - BURNOUT (ICD < 30):  Survival — solo vídeos/audios, nada activo.

Los umbrales son configurables mediante ThresholdConfig para recalibrar
cuando haya datos reales (ver tarea 3.7 de análisis de correlación).

Referencia: docs/TAREAS.md § 3.5.1

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from src.bio.models import DifficultyEnum, TaskTypeEnum


# ============================================================================
# 1. ENUMS Y TIPOS
# ============================================================================

class CognitiveZone(str, Enum):
    """
    Zonas cognitivas derivadas del ICD.

    Cada zona representa un estado fisiológico-cognitivo distinto y se
    mapea a una estrategia pedagógica que maximiza el rendimiento
    dentro de las capacidades disponibles ese día.
    """
    PEAK = "peak"
    NORMAL = "normal"
    FATIGUE = "fatigue"
    BURNOUT = "burnout"


class AIInteractionMode(str, Enum):
    """
    Modos de interacción de la IA según la zona cognitiva.

    Determina cómo el LLM se comporta: desde interrogar activamente
    (Socrático) hasta limitarse a presentar contenido pasivo.
    """
    SOCRATIC = "socratic"       # La IA te interroga, pide justificaciones
    GUIDED = "guided"           # La IA explica y guía con ejercicios
    SUPPORTIVE = "supportive"   # La IA repasa y refuerza, sin presión
    PASSIVE = "passive"         # La IA solo presenta contenido multimedia


# ============================================================================
# 2. CONFIGURACIÓN DE UMBRALES
# ============================================================================

@dataclass(frozen=True)
class ThresholdConfig:
    """
    Umbrales configurables para clasificar el ICD en zonas cognitivas.

    Los valores por defecto son hipótesis iniciales. Se recalibrarán
    con datos reales tras 30-60 días de tracking (tarea 3.7).

    Invariante: burnout_ceil < fatigue_ceil < normal_ceil <= 100
    """
    normal_ceil: float = 80.0   # ICD > normal_ceil  → PEAK
    fatigue_ceil: float = 50.0  # ICD > fatigue_ceil → NORMAL
    burnout_ceil: float = 30.0  # ICD > burnout_ceil → FATIGUE
                                # ICD <= burnout_ceil → BURNOUT

    def __post_init__(self) -> None:
        """Valida que los umbrales sean coherentes y estén ordenados."""
        if not (0 < self.burnout_ceil < self.fatigue_ceil < self.normal_ceil <= 100):
            raise ValueError(
                f"Los umbrales deben cumplir: "
                f"0 < burnout_ceil ({self.burnout_ceil}) "
                f"< fatigue_ceil ({self.fatigue_ceil}) "
                f"< normal_ceil ({self.normal_ceil}) <= 100"
            )


# ============================================================================
# 3. ESTRATEGIA PEDAGÓGICA
# ============================================================================

@dataclass(frozen=True)
class PedagogicalStrategy:
    """
    Estrategia pedagógica completa asociada a una zona cognitiva.

    Contiene toda la información necesaria para que el sistema
    (frontend + LLM) adapte la experiencia de estudio.

    Attributes:
        zone: Zona cognitiva clasificada (PEAK, NORMAL, FATIGUE, BURNOUT).
        name: Nombre corto de la estrategia (ej: "Deep Work").
        description: Explicación breve de la estrategia para el usuario.
        recommended_tasks: Tipos de tarea recomendados, ordenados por prioridad.
        max_difficulty: Dificultad máxima recomendada para la sesión.
        ai_mode: Modo de interacción de la IA.
        color: Color para representación visual en UI (hex).
        emoji: Emoji representativo para badges en UI.
        prompt_hint: Instrucción que se inyecta al system prompt del LLM
                     para adaptar su comportamiento a la zona cognitiva.
    """
    zone: CognitiveZone
    name: str
    description: str
    recommended_tasks: List[TaskTypeEnum]
    max_difficulty: DifficultyEnum
    ai_mode: AIInteractionMode
    color: str
    emoji: str
    prompt_hint: str


# ============================================================================
# 4. CATÁLOGO DE ESTRATEGIAS (constantes)
# ============================================================================

STRATEGY_PEAK = PedagogicalStrategy(
    zone=CognitiveZone.PEAK,
    name="Deep Work",
    description=(
        "Estado óptimo para aprendizaje profundo. "
        "Aprovecha para temas nuevos, matemáticas complejas y resolución "
        "de problemas difíciles. La IA te interrogará al estilo socrático."
    ),
    recommended_tasks=[
        TaskTypeEnum.MATH,
        TaskTypeEnum.THEORY_NEW,
        TaskTypeEnum.CREATIVE,
    ],
    max_difficulty=DifficultyEnum.EPIC,
    ai_mode=AIInteractionMode.SOCRATIC,
    color="#22c55e",   # verde
    emoji="🧠",
    prompt_hint=(
        "El usuario está en estado cognitivo PEAK (ICD > 80). "
        "Adopta un estilo socrático: NO des respuestas directas. "
        "Haz preguntas que fuercen razonamiento profundo, pide "
        "justificaciones formales y cuestiona sus supuestos. "
        "Prioriza temas nuevos y problemas desafiantes."
    ),
)

STRATEGY_NORMAL = PedagogicalStrategy(
    zone=CognitiveZone.NORMAL,
    name="Flow",
    description=(
        "Buen estado para práctica enfocada. "
        "Ideal para programación, ejercicios estándar y consolidar "
        "lo aprendido. La IA te guiará con explicaciones y ejercicios."
    ),
    recommended_tasks=[
        TaskTypeEnum.CODING,
        TaskTypeEnum.MATH,
        TaskTypeEnum.THEORY_NEW,
    ],
    max_difficulty=DifficultyEnum.HARD,
    ai_mode=AIInteractionMode.GUIDED,
    color="#3b82f6",   # azul
    emoji="⚡",
    prompt_hint=(
        "El usuario está en estado cognitivo NORMAL (ICD 50-80). "
        "Usa un estilo guiado: explica conceptos con claridad, "
        "proporciona ejercicios progresivos y da feedback constructivo. "
        "Puedes introducir temas nuevos pero con apoyo adicional."
    ),
)

STRATEGY_FATIGUE = PedagogicalStrategy(
    zone=CognitiveZone.FATIGUE,
    name="Review",
    description=(
        "Energía limitada. Enfócate en repasar material conocido, "
        "lectura de documentación y repaso espaciado (estilo Anki). "
        "La IA te apoyará sin presión."
    ),
    recommended_tasks=[
        TaskTypeEnum.REVIEW,
        TaskTypeEnum.CODING,
    ],
    max_difficulty=DifficultyEnum.MEDIUM,
    ai_mode=AIInteractionMode.SUPPORTIVE,
    color="#f59e0b",   # amarillo/naranja
    emoji="📖",
    prompt_hint=(
        "El usuario está en estado de FATIGA (ICD 30-50). "
        "Usa un estilo de apoyo: repasa material ya visto, refuerza "
        "conceptos con ejemplos sencillos y flashcards. NO introduzcas "
        "temas nuevos ni hagas preguntas complejas. Sé paciente."
    ),
)

STRATEGY_BURNOUT = PedagogicalStrategy(
    zone=CognitiveZone.BURNOUT,
    name="Survival",
    description=(
        "Capacidad cognitiva muy baja. Solo consumo pasivo: "
        "vídeos, podcasts o audios. Nada de input activo. "
        "Prioriza el descanso."
    ),
    recommended_tasks=[
        TaskTypeEnum.REVIEW,
    ],
    max_difficulty=DifficultyEnum.EASY,
    ai_mode=AIInteractionMode.PASSIVE,
    color="#ef4444",   # rojo
    emoji="🛌",
    prompt_hint=(
        "El usuario está en estado de BURNOUT (ICD < 30). "
        "Modo supervivencia: sugiere SOLO contenido pasivo como vídeos "
        "o audios. Si el usuario insiste en estudiar, recomiéndale "
        "descansar primero. Responde de forma breve y reconfortante. "
        "NO hagas preguntas ni propongas ejercicios."
    ),
)

# Mapa interno zona → estrategia para lookup rápido
_ZONE_STRATEGY_MAP = {
    CognitiveZone.PEAK: STRATEGY_PEAK,
    CognitiveZone.NORMAL: STRATEGY_NORMAL,
    CognitiveZone.FATIGUE: STRATEGY_FATIGUE,
    CognitiveZone.BURNOUT: STRATEGY_BURNOUT,
}


# ============================================================================
# 5. FUNCIONES PÚBLICAS
# ============================================================================

def classify_zone(
    icd_score: float,
    config: Optional[ThresholdConfig] = None,
) -> CognitiveZone:
    """
    Clasifica un ICD score en su zona cognitiva correspondiente.

    Aplica umbrales secuenciales de mayor a menor:
        ICD > normal_ceil  → PEAK
        ICD > fatigue_ceil → NORMAL
        ICD > burnout_ceil → FATIGUE
        ICD <= burnout_ceil → BURNOUT

    Args:
        icd_score: Valor del Índice Cognitivo Diario (0-100).
        config: Umbrales personalizados. Si es None, usa los valores por defecto.

    Returns:
        Zona cognitiva correspondiente al ICD.

    Raises:
        ValueError: Si icd_score no está en el rango [0, 100].
    """
    if not (0.0 <= icd_score <= 100.0):
        raise ValueError(
            f"icd_score debe estar en el rango [0, 100], recibido: {icd_score}"
        )

    if config is None:
        config = ThresholdConfig()

    if icd_score > config.normal_ceil:
        return CognitiveZone.PEAK
    elif icd_score > config.fatigue_ceil:
        return CognitiveZone.NORMAL
    elif icd_score > config.burnout_ceil:
        return CognitiveZone.FATIGUE
    else:
        return CognitiveZone.BURNOUT


def get_strategy(
    icd_score: float,
    config: Optional[ThresholdConfig] = None,
) -> PedagogicalStrategy:
    """
    Obtiene la estrategia pedagógica completa para un ICD score dado.

    Es la función principal del motor de decisión. Combina clasificación
    de zona + lookup de estrategia en un solo paso.

    Ejemplo de uso:
        >>> strategy = get_strategy(icd_score=85.0)
        >>> print(strategy.name)
        "Deep Work"
        >>> print(strategy.ai_mode)
        AIInteractionMode.SOCRATIC

    Args:
        icd_score: Valor del Índice Cognitivo Diario (0-100).
        config: Umbrales personalizados. Si es None, usa los valores por defecto.

    Returns:
        Objeto PedagogicalStrategy con toda la información de la estrategia.

    Raises:
        ValueError: Si icd_score no está en el rango [0, 100].
    """
    zone = classify_zone(icd_score, config)
    return _ZONE_STRATEGY_MAP[zone]


def get_strategy_for_record(
    icd_score: Optional[float],
    config: Optional[ThresholdConfig] = None,
) -> Optional[PedagogicalStrategy]:
    """
    Versión segura de get_strategy que acepta valores None.

    Útil cuando se trabaja directamente con registros de DailyBiometrics
    donde icd_score puede no haberse calculado aún.

    Args:
        icd_score: Valor del ICD (puede ser None si no se ha calculado).
        config: Umbrales personalizados.

    Returns:
        PedagogicalStrategy si el ICD está disponible, None en caso contrario.
    """
    if icd_score is None:
        return None
    return get_strategy(icd_score, config)


def get_all_strategies() -> List[PedagogicalStrategy]:
    """
    Retorna todas las estrategias ordenadas de mayor a menor ICD.

    Útil para renderizar en la UI la leyenda completa de zonas/estrategias.

    Returns:
        Lista de las 4 estrategias en orden: PEAK, NORMAL, FATIGUE, BURNOUT.
    """
    return [
        STRATEGY_PEAK,
        STRATEGY_NORMAL,
        STRATEGY_FATIGUE,
        STRATEGY_BURNOUT,
    ]


def get_threshold_ranges(
    config: Optional[ThresholdConfig] = None,
) -> List[Tuple[CognitiveZone, float, float]]:
    """
    Retorna los rangos numéricos de cada zona para visualización.

    Útil para renderizar barras de progreso o gauges en la UI
    con los rangos correctos.

    Args:
        config: Umbrales personalizados.

    Returns:
        Lista de tuplas (zona, límite_inferior, límite_superior).
        Ejemplo: [(PEAK, 80.0, 100.0), (NORMAL, 50.0, 80.0), ...]
    """
    if config is None:
        config = ThresholdConfig()

    return [
        (CognitiveZone.PEAK, config.normal_ceil, 100.0),
        (CognitiveZone.NORMAL, config.fatigue_ceil, config.normal_ceil),
        (CognitiveZone.FATIGUE, config.burnout_ceil, config.fatigue_ceil),
        (CognitiveZone.BURNOUT, 0.0, config.burnout_ceil),
    ]
