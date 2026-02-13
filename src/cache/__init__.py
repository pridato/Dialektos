"""
Cache y persistencia en Redis — Dialektos

- redis_client: Conexión Redis (get_redis).
- rag_semantic_cache: Caché semántico RAG (pregunta → respuesta por similitud).
- session_memory: Memoria conversacional persistida en listas Redis.
"""

from .redis_client import get_redis
from .rag_semantic_cache import RagSemanticCache
from .session_memory import RedisSessionMemory

__all__ = [
    "get_redis",
    "RagSemanticCache",
    "RedisSessionMemory",
]
