"""
Memoria de sesión en Redis — Listas por session_id

Almacena el estado de la conversación como lista de objetos JSON
{ "role": "user"|"assistant", "content": "..." } en la key
session:{session_id}. Permite persistir memoria entre requests.

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from src.cache.redis_client import get_redis

logger = logging.getLogger(__name__)

KEY_PREFIX = "session:"
DEFAULT_MAX_MESSAGES = 50  # Máximo mensajes en lista (LTRIM)
DEFAULT_TTL_SECONDS = 86400 * 7  # 7 días


class RedisSessionMemory:
    """
    Persistencia de memoria conversacional en listas Redis.
    Key: session:{session_id}, value: lista de JSON con role y content.
    """

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        *,
        max_messages: int = DEFAULT_MAX_MESSAGES,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self._redis = redis_client or get_redis()
        self.max_messages = max_messages
        self.ttl_seconds = ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"{KEY_PREFIX}{session_id}"

    def get(self, session_id: str) -> List[Dict[str, str]]:
        """
        Devuelve la lista de mensajes de la sesión (role, content).

        Returns:
            Lista de dicts [{"role": "user"|"assistant", "content": "..."}].
        """
        if not session_id or not session_id.strip():
            return []
        key = self._key(session_id.strip())
        try:
            raw_list = self._redis.lrange(key, 0, -1)
            if not raw_list:
                return []
            out: List[Dict[str, str]] = []
            for item in raw_list:
                try:
                    out.append(json.loads(item))
                except (json.JSONDecodeError, TypeError):
                    continue
            return out
        except Exception as e:
            logger.warning("RedisSessionMemory get error: %s", e)
            return []

    def append(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Añade un mensaje al final de la lista y aplica LTRIM + TTL."""
        if not session_id or not session_id.strip():
            return
        key = self._key(session_id.strip())
        msg: Dict[str, Any] = {"role": role, "content": content}
        if extra:
            msg.update(extra)
        try:
            self._redis.rpush(key, json.dumps(msg, ensure_ascii=False))
            self._redis.ltrim(key, -self.max_messages, -1)
            self._redis.expire(key, self.ttl_seconds)
        except Exception as e:
            logger.warning("RedisSessionMemory append error: %s", e)

    def set_messages(self, session_id: str, messages: List[Dict[str, str]]) -> None:
        """Sobrescribe la lista de mensajes de la sesión (útil tras cargar + RAG)."""
        if not session_id or not session_id.strip():
            return
        key = self._key(session_id.strip())
        try:
            self._redis.delete(key)
            for m in messages[-self.max_messages :]:
                self._redis.rpush(
                    key,
                    json.dumps(
                        {"role": m.get("role", "user"), "content": m.get("content", "")},
                        ensure_ascii=False,
                    ),
                )
            self._redis.expire(key, self.ttl_seconds)
        except Exception as e:
            logger.warning("RedisSessionMemory set_messages error: %s", e)

    def clear(self, session_id: str) -> None:
        """Borra la sesión."""
        if not session_id or not session_id.strip():
            return
        try:
            self._redis.delete(self._key(session_id.strip()))
        except Exception as e:
            logger.warning("RedisSessionMemory clear error: %s", e)
