"""
Cliente Redis — Conexión centralizada para cache y sesiones

Expone get_redis() para uso en API (ICD cache-aside), RAG semantic cache
y memoria conversacional por sesión.

Configuración vía entorno:
- REDIS_URL: opcional, default "redis://localhost:6379/0"

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

import os
from typing import Optional

import redis.asyncio as aioredis
import redis

# Sincrono para código que aún no es async (ej. retriever)
_redis_sync: Optional[redis.Redis] = None
_redis_async: Optional[aioredis.Redis] = None


def get_redis_url() -> str:
    """URL de conexión Redis desde entorno."""
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_redis(*, use_async: bool = False):
    """
    Obtiene un cliente Redis (singleton).

    Args:
        use_async: Si True devuelve redis.asyncio.Redis para FastAPI async.

    Returns:
        redis.Redis o redis.asyncio.Redis según use_async.
    """
    global _redis_sync, _redis_async
    url = get_redis_url()
    if use_async:
        if _redis_async is None:
            _redis_async = aioredis.from_url(url, decode_responses=True)
        return _redis_async
    if _redis_sync is None:
        _redis_sync = redis.from_url(url, decode_responses=True)
    return _redis_sync
