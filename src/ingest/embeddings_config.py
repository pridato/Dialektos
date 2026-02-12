"""
Configuración Centralizada de Modelos de Embeddings

Este módulo define los modelos de embeddings disponibles para el sistema RAG,
sus características y funciones de validación.

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


# ============================================================================
# TIPOS Y ENUMERACIONES
# ============================================================================

class EmbeddingQuality(Enum):
    """Niveles de calidad de embeddings (trade-off velocidad vs precisión)."""
    FAST = "fast"           # Rápido pero menos preciso (~80-100MB)
    BALANCED = "balanced"   # Balance calidad/velocidad (~400-500MB)
    HIGH = "high"           # Máxima calidad (~1-2GB)


class Language(Enum):
    """Idiomas soportados por los modelos."""
    MULTILINGUAL = "multilingual"
    SPANISH = "spanish"
    ENGLISH = "english"


# ============================================================================
# MODELO DE DATOS: Configuración de Embeddings
# ============================================================================

@dataclass
class EmbeddingModelConfig:
    """
    Configuración de un modelo de embeddings.
    
    Attributes:
        name: Nombre del modelo en HuggingFace
        dimension: Dimensionalidad de los vectores de salida
        size_mb: Tamaño aproximado del modelo en disco (MB)
        quality: Nivel de calidad (fast/balanced/high)
        languages: Lista de idiomas soportados
        description: Descripción breve del modelo
        recommended_for: Casos de uso recomendados
        max_seq_length: Longitud máxima de secuencia (tokens)
    """
    name: str
    dimension: int
    size_mb: int
    quality: EmbeddingQuality
    languages: List[Language]
    description: str
    recommended_for: List[str]
    max_seq_length: int = 512


# ============================================================================
# CATÁLOGO DE MODELOS DISPONIBLES
# ============================================================================

AVAILABLE_MODELS: Dict[str, EmbeddingModelConfig] = {
    
    # ========================================================================
    # MODELOS MULTILINGÜES (Recomendados para español + inglés)
    # ========================================================================
    
    "paraphrase-multilingual-mpnet-base-v2": EmbeddingModelConfig(
        name="paraphrase-multilingual-mpnet-base-v2",
        dimension=768,
        size_mb=420,
        quality=EmbeddingQuality.BALANCED,
        languages=[Language.MULTILINGUAL],
        description="Modelo multilingüe de alta calidad optimizado para tareas de búsqueda semántica. "
                   "Excelente balance entre precisión y velocidad.",
        recommended_for=[
            "Búsqueda semántica en español e inglés",
            "Documentos académicos multilingües",
            "Uso general (recomendado para Dialektos)"
        ],
        max_seq_length=128
    ),
    
    "paraphrase-multilingual-MiniLM-L12-v2": EmbeddingModelConfig(
        name="paraphrase-multilingual-MiniLM-L12-v2",
        dimension=384,
        size_mb=120,
        quality=EmbeddingQuality.FAST,
        languages=[Language.MULTILINGUAL],
        description="Versión ligera del modelo multilingüe. Ideal para prototipos rápidos.",
        recommended_for=[
            "Prototipado rápido",
            "Recursos limitados",
            "Testing inicial"
        ],
        max_seq_length=128
    ),
    
    "distiluse-base-multilingual-cased-v2": EmbeddingModelConfig(
        name="distiluse-base-multilingual-cased-v2",
        dimension=512,
        size_mb=250,
        quality=EmbeddingQuality.BALANCED,
        languages=[Language.MULTILINGUAL],
        description="Modelo multilingüe destilado de Universal Sentence Encoder. "
                   "Buena opción intermedia.",
        recommended_for=[
            "Balance velocidad/calidad",
            "Documentos técnicos multilingües"
        ],
        max_seq_length=128
    ),
    
    # ========================================================================
    # MODELOS ESPECIALIZADOS EN INGLÉS (Alta calidad)
    # ========================================================================
    
    "all-mpnet-base-v2": EmbeddingModelConfig(
        name="all-mpnet-base-v2",
        dimension=768,
        size_mb=420,
        quality=EmbeddingQuality.HIGH,
        languages=[Language.ENGLISH],
        description="Modelo de máxima calidad para inglés. Mejor performance en benchmarks.",
        recommended_for=[
            "Documentos exclusivamente en inglés",
            "Máxima precisión requerida"
        ],
        max_seq_length=384
    ),
    
    "all-MiniLM-L6-v2": EmbeddingModelConfig(
        name="all-MiniLM-L6-v2",
        dimension=384,
        size_mb=80,
        quality=EmbeddingQuality.FAST,
        languages=[Language.ENGLISH],
        description="Modelo ligero y rápido para inglés. Default de ChromaDB.",
        recommended_for=[
            "Velocidad crítica",
            "Testing rápido",
            "Recursos muy limitados"
        ],
        max_seq_length=256
    ),
    
    # ========================================================================
    # MODELOS DOMAIN-SPECIFIC
    # ========================================================================
    
    "multi-qa-mpnet-base-dot-v1": EmbeddingModelConfig(
        name="multi-qa-mpnet-base-dot-v1",
        dimension=768,
        size_mb=420,
        quality=EmbeddingQuality.HIGH,
        languages=[Language.ENGLISH],
        description="Especializado en Question-Answering. Optimizado para queries cortas "
                   "vs documentos largos.",
        recommended_for=[
            "Sistemas RAG de pregunta-respuesta",
            "Búsqueda asimétrica (query corta, documento largo)"
        ],
        max_seq_length=512
    ),
}


# ============================================================================
# CONFIGURACIÓN POR DEFECTO
# ============================================================================

DEFAULT_MODEL = "paraphrase-multilingual-mpnet-base-v2"
FALLBACK_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def get_model_config(model_name: str) -> Optional[EmbeddingModelConfig]:
    """
    Obtiene la configuración de un modelo por su nombre.
    
    Args:
        model_name: Nombre del modelo (debe estar en AVAILABLE_MODELS)
        
    Returns:
        Configuración del modelo o None si no existe
        
    Example:
        >>> config = get_model_config("paraphrase-multilingual-mpnet-base-v2")
        >>> print(config.dimension)
        768
    """
    return AVAILABLE_MODELS.get(model_name)


def list_available_models(
    quality: Optional[EmbeddingQuality] = None,
    language: Optional[Language] = None
) -> List[str]:
    """
    Lista los modelos disponibles con filtros opcionales.
    
    Args:
        quality: Filtrar por nivel de calidad (fast/balanced/high)
        language: Filtrar por idioma soportado
        
    Returns:
        Lista de nombres de modelos que cumplen los criterios
        
    Example:
        >>> # Listar todos los modelos multilingües balanceados
        >>> models = list_available_models(
        ...     quality=EmbeddingQuality.BALANCED,
        ...     language=Language.MULTILINGUAL
        ... )
    """
    models = []
    
    for name, config in AVAILABLE_MODELS.items():
        # Filtrar por calidad si se especifica
        if quality and config.quality != quality:
            continue
        
        # Filtrar por idioma si se especifica
        if language and language not in config.languages:
            continue
        
        models.append(name)
    
    return models


def validate_model(model_name: str) -> bool:
    """
    Valida si un modelo está disponible en el catálogo.
    
    Args:
        model_name: Nombre del modelo a validar
        
    Returns:
        True si el modelo existe, False en caso contrario
        
    Example:
        >>> validate_model("paraphrase-multilingual-mpnet-base-v2")
        True
        >>> validate_model("modelo-inexistente")
        False
    """
    return model_name in AVAILABLE_MODELS


def get_recommended_model_for_dialektos() -> str:
    """
    Retorna el modelo recomendado para el proyecto Dialektos.
    
    Criterios de selección:
    - Soporte multilingüe (español + inglés)
    - Balance calidad/velocidad
    - Dimensionalidad óptima para búsqueda semántica
    - Tamaño razonable (~400MB)
    
    Returns:
        Nombre del modelo recomendado
    """
    return DEFAULT_MODEL


def print_model_info(model_name: str) -> None:
    """
    Imprime información detallada sobre un modelo.
    
    Args:
        model_name: Nombre del modelo
        
    Example:
        >>> print_model_info("paraphrase-multilingual-mpnet-base-v2")
        📊 Modelo: paraphrase-multilingual-mpnet-base-v2
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ...
    """
    config = get_model_config(model_name)
    
    if not config:
        print(f"❌ Modelo '{model_name}' no encontrado en el catálogo")
        return
    
    print(f"\n📊 Modelo: {config.name}")
    print("━" * 60)
    print(f"🔹 Dimensión: {config.dimension}")
    print(f"🔹 Tamaño: ~{config.size_mb} MB")
    print(f"🔹 Calidad: {config.quality.value}")
    print(f"🔹 Idiomas: {', '.join([lang.value for lang in config.languages])}")
    print(f"🔹 Max tokens: {config.max_seq_length}")
    print(f"\n📝 Descripción:")
    print(f"   {config.description}")
    print(f"\n✅ Recomendado para:")
    for use_case in config.recommended_for:
        print(f"   • {use_case}")
    print("━" * 60)


def compare_models(model_names: List[str]) -> None:
    """
    Compara múltiples modelos lado a lado.
    
    Args:
        model_names: Lista de nombres de modelos a comparar
        
    Example:
        >>> compare_models([
        ...     "paraphrase-multilingual-mpnet-base-v2",
        ...     "all-MiniLM-L6-v2"
        ... ])
    """
    print("\n📊 COMPARACIÓN DE MODELOS")
    print("=" * 80)
    print(f"{'Modelo':<45} {'Dim':<8} {'Tamaño':<10} {'Calidad':<10}")
    print("-" * 80)
    
    for name in model_names:
        config = get_model_config(name)
        if config:
            print(f"{name:<45} {config.dimension:<8} {config.size_mb}MB{'':<6} {config.quality.value:<10}")
        else:
            print(f"{name:<45} {'N/A':<8} {'N/A':<10} {'N/A':<10}")
    
    print("=" * 80)


# ============================================================================
# FUNCIÓN PRINCIPAL (Demo)
# ============================================================================

def main():
    """
    Demo de las funciones del módulo.
    """
    print("\n🤖 CONFIGURACIÓN DE EMBEDDINGS - DIALEKTOS\n")
    
    # Mostrar modelo recomendado
    recommended = get_recommended_model_for_dialektos()
    print(f"✨ Modelo recomendado para Dialektos: {recommended}\n")
    print_model_info(recommended)
    
    # Listar modelos multilingües
    print("\n\n🌍 MODELOS MULTILINGÜES DISPONIBLES:")
    print("-" * 60)
    multilingual_models = list_available_models(language=Language.MULTILINGUAL)
    for model in multilingual_models:
        config = get_model_config(model)
        print(f"  • {model}")
        print(f"    {config.quality.value} | {config.dimension}D | ~{config.size_mb}MB")
    
    # Comparar modelos rápidos vs balanceados
    print("\n\n⚖️ COMPARACIÓN: FAST vs BALANCED")
    fast_models = list_available_models(quality=EmbeddingQuality.FAST)
    balanced_models = list_available_models(quality=EmbeddingQuality.BALANCED)
    compare_models(fast_models[:2] + balanced_models[:2])


if __name__ == "__main__":
    main()
