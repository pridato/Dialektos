"""
Cliente Web Search — Integración con Tavily API

Encapsula la búsqueda web mediante Tavily para el Router de Búsqueda.
Cuando la similitud en ChromaDB es baja (< 0.7), el Retriever activa
este módulo para obtener contexto de la web en lugar de rechazar la pregunta.

Componentes:
    - WebSearchResult: Modelo Pydantic de un resultado de búsqueda.
    - TavilyWebSearch: Cliente que encapsula la API de Tavily.

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import logging
import os
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

logger = logging.getLogger(__name__)


# ─── Modelo Pydantic ──────────────────────────────────────────

class WebSearchResult(BaseModel):
    """
    Resultado de búsqueda web de Tavily.

    Refleja la estructura de cada item en response.results de la API.

    Attributes:
        title: Título del resultado (página web).
        url: URL del recurso.
        content: Fragmento de contenido más relevante para la query.
        score: Puntuación de relevancia (0-1) asignada por Tavily.
    """
    title: str
    url: str
    content: str
    score: float = Field(default=0.0, ge=0.0, le=1.0)


# ─── Cliente Tavily ───────────────────────────────────────────

class TavilyWebSearch:
    """
    Cliente para búsqueda web mediante Tavily API.

    Usado por el Search Router cuando la similitud vectorial en ChromaDB
    es inferior al umbral configurado (p. ej. 0.7).

    Si TAVILY_API_KEY no está definida, search() retorna lista vacía
    y se loguea un warning.

    Example:
        >>> client = TavilyWebSearch()
        >>> results = client.search("¿Qué es un espacio vectorial?")
        >>> for r in results:
        ...     print(f"[{r.score:.2f}] {r.title}: {r.url}")
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Inicializa el cliente Tavily.

        Args:
            api_key: Clave API de Tavily. Si es None, se carga desde
                TAVILY_API_KEY en .env. Si no existe, el cliente queda
                deshabilitado (search retornará []).
        """
        self._api_key: Optional[str] = api_key or os.getenv("TAVILY_API_KEY")
        self._client = None

        if self._api_key:
            try:
                from tavily import TavilyClient
                self._client = TavilyClient(api_key=self._api_key)
                logger.info("TavilyWebSearch inicializado correctamente")
            except ImportError as e:
                logger.warning(
                    f"tavily-python no instalado. Web search deshabilitado: {e}"
                )
                self._client = None
        else:
            logger.warning(
                "TAVILY_API_KEY no configurada. Web search deshabilitado. "
                "Obtén una en https://app.tavily.com"
            )

    @property
    def is_available(self) -> bool:
        """True si el cliente Tavily está listo para usar."""
        return self._client is not None

    def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[WebSearchResult]:
        """
        Ejecuta una búsqueda web en Tavily.

        Args:
            query: Texto de búsqueda (pregunta o frase).
            max_results: Número máximo de resultados (default: 5).
                Tavily acepta hasta 20.

        Returns:
            Lista de WebSearchResult. Vacía si el cliente no está
            disponible, hay error de API, o no hay resultados.
        """
        if not self._client:
            return []

        if not query or not query.strip():
            logger.warning("Query vacío proporcionado a TavilyWebSearch.search")
            return []

        try:
            response = self._client.search(
                query=query.strip(),
                max_results=min(max_results, 20),
                search_depth="basic",
            )

            # Tavily puede devolver dict o objeto
            results_raw = (
                response.get("results", [])
                if isinstance(response, dict)
                else (getattr(response, "results", None) or [])
            )
            results: List[WebSearchResult] = []

            for item in results_raw[:max_results]:
                if isinstance(item, dict):
                    title = item.get("title", "") or ""
                    url = item.get("url", "") or ""
                    content = item.get("content", "") or ""
                    score = float(item.get("score", 0.0))
                else:
                    title = getattr(item, "title", "") or ""
                    url = getattr(item, "url", "") or ""
                    content = getattr(item, "content", "") or ""
                    score = float(getattr(item, "score", 0.0))
                results.append(
                    WebSearchResult(
                        title=title,
                        url=url,
                        content=content,
                        score=score,
                    )
                )

            logger.info(
                f"Tavily search: {len(results)} resultados para "
                f"query='{query[:50]}...'"
            )
            return results

        except Exception as e:
            logger.error(f"Error en Tavily search: {e}")
            return []
