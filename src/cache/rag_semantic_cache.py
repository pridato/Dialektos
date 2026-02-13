"""
Caché semántico RAG — Pregunta/respuesta por similitud

Usa ChromaDB para búsqueda por similitud de preguntas y Redis para
almacenar la respuesta. Si una pregunta muy similar ya fue respondida,
se devuelve la respuesta cacheada sin llamar al LLM.

Flujo:
  1. Embed de la pregunta → búsqueda en colección "rag_semantic_cache".
  2. Si score >= umbral → recuperar de Redis rag:cache:{cache_id} y devolver.
  3. Si no → ejecutar RAG, guardar en ChromaDB (doc=pregunta, metadata={cache_id})
     y en Redis (key=rag:cache:{cache_id}, value=JSON respuesta).

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, Optional

from src.cache.redis_client import get_redis

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "rag:cache:"
DEFAULT_SIMILARITY_THRESHOLD = 0.92
DEFAULT_TTL_SECONDS = 86400  # 24 h


class RagSemanticCache:
    """
    Caché por similitud: ChromaDB (índice de preguntas) + Redis (respuestas).
    """

    def __init__(
        self,
        db: Any,  # ChromaDBPersistence
        redis_client: Optional[Any] = None,
        *,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        cache_collection_name: str = "rag_semantic_cache",
    ) -> None:
        self.db = db
        self._redis = redis_client or get_redis()
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self._cache_collection = self._get_or_create_cache_collection(
            cache_collection_name
        )

    def _get_or_create_cache_collection(self, name: str):  # noqa: ANN201
        try:
            return self.db.client.get_collection(
                name=name,
                embedding_function=self.db.embedding_function,
            )
        except Exception:
            return self.db.client.create_collection(
                name=name,
                embedding_function=self.db.embedding_function,
                metadata={"hnsw:space": "cosine"},
            )

    def get(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Busca una respuesta cacheada por similitud con la pregunta.

        Returns:
            Dict con answer, sources, had_context, etc. si hay hit; None si no.
        """
        if not question or not question.strip():
            return None
        try:
            results = self._cache_collection.query(
                query_texts=[question.strip()],
                n_results=1,
            )
            ids = results["ids"][0] if results["ids"] else []
            distances = results["distances"][0] if results["distances"] else []
            if not ids or not distances:
                return None
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # score = 1 - (distance / 2) para normalizar a [0, 1]
            dist = float(distances[0])
            score = 1.0 - (dist / 2.0) if dist <= 2.0 else 0.0
            if score < self.similarity_threshold:
                return None
            cache_id = ids[0]
            key = f"{REDIS_KEY_PREFIX}{cache_id}"
            raw = self._redis.get(key)
            if not raw:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.warning("RAG semantic cache get error: %s", e)
            return None

    def set(self, question: str, payload: Dict[str, Any]) -> None:
        """Guarda pregunta en ChromaDB y respuesta en Redis."""
        if not question or not question.strip():
            return
        cache_id = str(uuid.uuid4())
        key = f"{REDIS_KEY_PREFIX}{cache_id}"
        try:
            self._cache_collection.add(
                documents=[question.strip()],
                metadatas=[{"cache_id": cache_id}],
                ids=[cache_id],
            )
            self._redis.setex(
                key,
                self.ttl_seconds,
                json.dumps(payload, ensure_ascii=False),
            )
            logger.debug("RAG cache set: %s", cache_id)
        except Exception as e:
            logger.warning("RAG semantic cache set error: %s", e)
