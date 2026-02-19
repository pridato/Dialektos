"""
Módulo de caché Redis para planes de estudio

Proporciona funciones para guardar y recuperar planes de estudio desde Redis,
evitando llamadas innecesarias al LLM cuando el plan ya ha sido generado.

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import json
import hashlib
from typing import Optional
import redis
from src.brain.mindmapper import StudyPlanResult

# Configuración de Redis
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None  # Configurar si Redis requiere autenticación

# TTL por defecto: 30 días (los planes de estudio no cambian frecuentemente)
DEFAULT_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 días

# Prefijo para las claves de caché
CACHE_KEY_PREFIX = "study_plan:"


def _get_redis_client() -> redis.Redis:
    """
    Crea y retorna un cliente Redis.
    
    Returns:
        Cliente Redis configurado.
    """
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,  # Decodifica automáticamente strings
            socket_connect_timeout=2,  # Timeout corto para evitar bloqueos
        )
        # Verificar conexión
        client.ping()
        return client
    except (redis.ConnectionError, redis.TimeoutError) as e:
        # Si Redis no está disponible, retornar None (fallback a LLM directo)
        print(f"⚠️  Redis no disponible: {e}. Usando LLM directo sin caché.")
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
        print(f"⚠️  Error leyendo caché: {e}. Usando LLM directo.")
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
        print(f"⚠️  Error guardando en caché: {e}. Plan generado pero no guardado en caché.")
        return False
