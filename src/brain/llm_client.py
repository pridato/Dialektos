"""
Cliente LLM — Conexión básica con GPT-4o mini

Proporciona una interfaz simple para consultar el LLM.
La función principal ``query_llm()`` acepta una pregunta en texto plano
y retorna la respuesta del modelo.

Componentes internos:
    1. Configuración — constantes del modelo y system prompt por defecto.
    2. Singleton ``_get_client()`` — inicialización lazy del cliente OpenAI.
    3. ``query_llm()`` — función pública que usa todo el sistema.

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

# ─── Cargar variables de entorno (.env) ──────────────────────
load_dotenv()

# ─── Configuración ───────────────────────────────────────────
DEFAULT_MODEL: str = "gpt-4o-mini"
DEFAULT_TEMPERATURE: float = 0.7
DEFAULT_MAX_TOKENS: int = 1024

SYSTEM_PROMPT: str = (
    "Eres Dialektos, un asistente de estudio universitario especializado "
    "en Ciencia de Datos, Matemáticas y Física. Responde en español de forma "
    "clara y rigurosa. Si no sabes algo, dilo honestamente."
)

# ─── Cliente Singleton ───────────────────────────────────────
_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """
    Inicialización lazy del cliente OpenAI.

    Se crea una única instancia (singleton) para reutilizar la conexión
    HTTP subyacente entre llamadas, evitando overhead de reconexión.

    Returns:
        Instancia configurada de ``OpenAI``.

    Raises:
        ValueError: Si ``OPENAI_API_KEY`` no está configurada en ``.env``
                    ni como variable de entorno.
    """
    global _client
    if _client is None:
        api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY no encontrada. "
                "Configúrala en tu archivo .env o como variable de entorno."
            )
        _client = OpenAI(api_key=api_key)
    return _client


# ─── Función Principal ───────────────────────────────────────
def query_llm(
    pregunta: str,
    *,
    system_prompt: str = SYSTEM_PROMPT,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """
    Envía una pregunta al LLM y retorna la respuesta como texto.

    Args:
        pregunta: La pregunta del usuario en texto plano.
        system_prompt: Instrucciones de comportamiento para el modelo.
            Por defecto usa el prompt base de Dialektos.
        model: Identificador del modelo de OpenAI a utilizar.
        temperature: Creatividad de la respuesta
            (0.0 = determinista, 1.0 = creativo).
        max_tokens: Límite máximo de tokens en la respuesta.

    Returns:
        Texto de la respuesta del modelo.

    Raises:
        ValueError: Si la pregunta está vacía o la API key no existe.
        OpenAIError: Si hay un error de comunicación con la API.

    Example:
        >>> respuesta = query_llm("¿Qué es una integral definida?")
        >>> print(respuesta)
    """
    if not pregunta.strip():
        raise ValueError("La pregunta no puede estar vacía.")

    client: OpenAI = _get_client()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": pregunta},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    except OpenAIError as e:
        raise OpenAIError(f"Error al consultar el LLM: {e}") from e


# ─── Chat interactivo ────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Dialektos — Chat con GPT-4o mini")
    print("  Escribe 'salir' para terminar.")
    print("=" * 60)

    while True:
        try:
            pregunta: str = input("\nTú: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nHasta luego.")
            break

        if pregunta.lower() in ("salir", "exit", "q"):
            print("\nHasta luego.")
            break

        if not pregunta:
            continue

        try:
            respuesta: str = query_llm(pregunta)
            print(f"\nDialektos: {respuesta}")
        except ValueError as e:
            print(f"\n✗ Error de configuración: {e}")
        except OpenAIError as e:
            print(f"\n✗ Error de API: {e}")
