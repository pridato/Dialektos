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

        La inicialización del cliente HTTP es lazy (se hace solo cuando se llama a search()).
        Esto evita errores de inicialización si hay problemas de compatibilidad.

        Args:
            api_key: Clave API de Tavily. Si es None, se carga desde
                TAVILY_API_KEY en .env. Si no existe, el cliente queda
                deshabilitado (search retornará []).
        """
        self._api_key: Optional[str] = api_key or os.getenv("TAVILY_API_KEY")
        self._client = None
        self._initialization_error: Optional[str] = None

        if not self._api_key:
            logger.warning(
                "TAVILY_API_KEY no configurada. Web search deshabilitado. "
                "Obtén una en https://app.tavily.com"
            )

    def _ensure_client_initialized(self) -> bool:
        """
        Inicializa el cliente Tavily de forma lazy si aún no está inicializado.
        
        Returns:
            True si el cliente está disponible, False en caso contrario.
        """
        if self._client is not None:
            return True
        
        if self._initialization_error:
            # Ya intentamos inicializar y falló, no intentar de nuevo
            return False
        
        if not self._api_key:
            return False
        
        try:
            from tavily import TavilyClient
            
            # Verificar si hay variables de entorno de proxies que puedan causar problemas
            proxy_vars = [
                os.getenv("HTTP_PROXY"),
                os.getenv("HTTPS_PROXY"),
                os.getenv("http_proxy"),
                os.getenv("https_proxy"),
                os.getenv("TAVILY_HTTP_PROXY"),
                os.getenv("TAVILY_HTTPS_PROXY"),
            ]
            has_proxy_config = any(proxy_vars)
            
            # Intentar inicializar TavilyClient
            try:
                self._client = TavilyClient(api_key=self._api_key)
                logger.info("TavilyWebSearch inicializado correctamente")
                return True
            except TypeError as e:
                # Manejar errores de argumentos inesperados (como proxies)
                error_msg = str(e).lower()
                if "proxies" in error_msg or "unexpected keyword" in error_msg:
                    self._initialization_error = (
                        f"Error de compatibilidad con TavilyClient relacionado con proxies: {e}. "
                        f"Variables de proxy detectadas: {has_proxy_config}. "
                        "Considera actualizar tavily-python: pip install --upgrade tavily-python"
                    )
                    logger.warning(self._initialization_error)
                    return False
                else:
                    # Re-lanzar otros errores TypeError
                    raise
        except ImportError as e:
            self._initialization_error = f"tavily-python no instalado: {e}"
            logger.warning(f"{self._initialization_error}. Web search deshabilitado.")
            return False
        except Exception as e:
            self._initialization_error = f"Error al inicializar TavilyClient: {e}"
            logger.error(f"{self._initialization_error}. Web search deshabilitado.")
            return False
    
    @property
    def is_available(self) -> bool:
        """True si el cliente Tavily está listo para usar."""
        return self._ensure_client_initialized()

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
        if not self._ensure_client_initialized():
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
