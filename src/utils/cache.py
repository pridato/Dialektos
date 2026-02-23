"""
Módulo de caché Redis para planes de estudio

Proporciona funciones para guardar y recuperar planes de estudio desde Redis,
evitando llamadas innecesarias al LLM cuando el plan ya ha sido generado.

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import hashlib
import json
import logging
from typing import Optional

import redis

from src.cache.redis_client import get_redis, get_redis_url
from src.brain.mindmapper import StudyPlanResult

logger = logging.getLogger(__name__)

# TTL por defecto: 30 días (los planes de estudio no cambian frecuentemente)
DEFAULT_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 días

# Prefijo para las claves de caché
CACHE_KEY_PREFIX = "study_plan:"


def _get_redis_client() -> Optional[redis.Redis]:
    """
    Crea y retorna un cliente Redis.

    Returns:
        Cliente Redis configurado.
    """
    try:
        client = get_redis()
        # Verificar conexión
        client.ping()
        return client
    except (redis.ConnectionError, redis.TimeoutError) as e:
        # Si Redis no está disponible, retornar None (fallback a LLM directo)
        logger.warning(
            "Redis no disponible en %s: %s. Usando LLM directo sin caché.",
            get_redis_url(),
            e,
        )
        return None


def _generate_cache_key(text: str, user_level: Optional[str] = None) -> str:
    """
    Genera una clave única para el caché basada en el texto y nivel del usuario.

    Args:
        text: Texto del objetivo del plan de estudio.
        user_level: Nivel del usuario (opcional).

    Returns:
        Clave de caché única.
    """
    # Normalizar texto (lowercase, strip)
    normalized_text = text.strip().lower()

    # Crear hash del texto + nivel
    cache_input = f"{normalized_text}:{user_level or 'auto'}"
    cache_hash = hashlib.sha256(cache_input.encode()).hexdigest()

    return f"{CACHE_KEY_PREFIX}{cache_hash}"


def get_study_plan_from_cache(
    text: str,
    user_level: Optional[str] = None
) -> Optional[StudyPlanResult]:
    """
    Intenta recuperar un plan de estudio desde Redis.

    Args:
        text: Texto del objetivo del plan de estudio.
        user_level: Nivel del usuario (opcional).

    Returns:
        StudyPlanResult si existe en caché, None si no existe o Redis no está disponible.
    """
    client = _get_redis_client()
    if client is None:
        return None

    try:
        cache_key = _generate_cache_key(text, user_level)
        cached_data = client.get(cache_key)

        if cached_data is None:
            return None

        # Deserializar JSON a StudyPlanResult
        data = json.loads(cached_data)
        return StudyPlanResult.model_validate(data)

    except (redis.RedisError, json.JSONDecodeError, ValueError) as e:
        # Si hay error al leer caché, continuar sin caché
        logger.warning("Error leyendo caché de study plan: %s. Usando LLM directo.", e)
        return None


def save_study_plan_to_cache(
    text: str,
    plan: StudyPlanResult,
    user_level: Optional[str] = None,
    ttl: int = DEFAULT_TTL_SECONDS
) -> bool:
    """
    Guarda un plan de estudio en Redis.

    Args:
        text: Texto del objetivo del plan de estudio.
        plan: StudyPlanResult a guardar.
        user_level: Nivel del usuario (opcional).
        ttl: Tiempo de vida en segundos (por defecto 30 días).

    Returns:
        True si se guardó exitosamente, False si Redis no está disponible o hubo error.
    """
    client = _get_redis_client()
    if client is None:
        return False

    try:
        cache_key = _generate_cache_key(text, user_level)

        # Serializar StudyPlanResult a JSON
        plan_dict = plan.model_dump()
        plan_json = json.dumps(plan_dict)

        # Guardar en Redis con TTL
        client.setex(cache_key, ttl, plan_json)
        return True

    except (redis.RedisError, ValueError) as e:
        # Si hay error al guardar caché, continuar sin caché
        logger.warning(
            "Error guardando en caché de study plan: %s. Plan generado pero no guardado en caché.",
            e,
        )
        return False
