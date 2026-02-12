"""
Gestión del Perfil de Usuario — Carga e inyección en System Prompts

Este módulo gestiona la carga del perfil de usuario desde un archivo JSON
y su integración en los system prompts para personalizar las respuestas
del asistente según el contexto del usuario.

Componentes:
    - load_user_profile(): Carga el JSON con manejo de errores
    - build_enriched_system_prompt(): Construye prompt enriquecido
    - get_user_profile(): Singleton/cache para evitar múltiples lecturas

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ─── Configuración ───────────────────────────────────────────
PROFILE_FILE_PATH: Path = Path(__file__).parent.parent.parent / "config" / "user_profile.json"

# Cache del perfil en memoria (singleton)
_profile_cache: Optional[Dict] = None


def load_user_profile() -> Optional[Dict]:
    """
    Carga el perfil de usuario desde el archivo JSON.

    Si el archivo no existe o está mal formado, retorna None y registra
    un warning. Esto permite que el sistema funcione sin perfil (fallback).

    Returns:
        Diccionario con el perfil del usuario o None si hay error.

    Example:
        >>> profile = load_user_profile()
        >>> if profile:
        ...     print(f"Rol: {profile['user_profile']['identity']['current_role']}")
    """
    global _profile_cache

    # Si ya está en cache, retornarlo
    if _profile_cache is not None:
        return _profile_cache

    # Intentar cargar el archivo
    if not PROFILE_FILE_PATH.exists():
        logger.warning(
            f"Archivo de perfil no encontrado: {PROFILE_FILE_PATH}. "
            "Usando prompts base sin personalización."
        )
        _profile_cache = None
        return None

    try:
        with open(PROFILE_FILE_PATH, "r", encoding="utf-8") as f:
            data: Dict = json.load(f)

        # Validar estructura básica
        if "user_profile" not in data:
            logger.error(
                "El archivo de perfil no contiene la clave 'user_profile'. "
                "Usando prompts base."
            )
            _profile_cache = None
            return None

        _profile_cache = data
        logger.info("Perfil de usuario cargado correctamente")
        return data

    except json.JSONDecodeError as e:
        logger.error(
            f"Error al parsear JSON del perfil: {e}. "
            "Usando prompts base sin personalización."
        )
        _profile_cache = None
        return None

    except Exception as e:
        logger.error(
            f"Error inesperado al cargar perfil: {e}. "
            "Usando prompts base sin personalización."
        )
        _profile_cache = None
        return None


def build_enriched_system_prompt(base_prompt: str, profile: Optional[Dict] = None) -> str:
    """
    Construye un system prompt enriquecido con información del perfil del usuario.

    Si no se proporciona perfil o está vacío, retorna el prompt base sin modificar.
    Extrae información relevante del perfil y la formatea en una sección
    estructurada que se añade al prompt base.

    Args:
        base_prompt: El system prompt base a enriquecer.
        profile: Diccionario con el perfil del usuario. Si es None, intenta
            cargarlo automáticamente.

    Returns:
        System prompt enriquecido con información del perfil.

    Example:
        >>> base = "Eres Dialektos..."
        >>> enriched = build_enriched_system_prompt(base)
        >>> # Ahora incluye información del perfil del usuario
    """
    if profile is None:
        profile = load_user_profile()

    if not profile or "user_profile" not in profile:
        return base_prompt

    up: Dict = profile["user_profile"]

    # Extraer información de identidad
    identity: Dict = up.get("identity", {})
    current_role: str = identity.get("current_role", "No especificado")
    occupation: str = identity.get("occupation", "No especificado")
    lang_prof: Dict = identity.get("language_proficiency", {})
    native_lang: str = lang_prof.get("native", "No especificado")
    english_level: str = lang_prof.get("english", "No especificado")

    # Extraer objetivos profesionales
    career: Dict = up.get("career_goals", {})
    primary_objective: str = career.get("primary_objective", "No especificado")
    interests: list = career.get("interests", [])

    # Extraer base de conocimiento
    knowledge: Dict = up.get("knowledge_base", {})
    strengths: list = knowledge.get("strengths", [])
    current_focus: str = knowledge.get("current_focus", "No especificado")

    # Extraer preferencias de aprendizaje
    learning: Dict = up.get("learning_preferences", {})
    pedagogical_style: str = learning.get("pedagogical_style", "No especificado")
    instruction_rules: list = learning.get("instruction_rules", [])
    critical_thinking: list = learning.get("critical_thinking", [])

    # Construir sección del perfil
    profile_section = f"""
--- PERFIL DEL USUARIO ---
Rol actual: {current_role}
Ocupación: {occupation}
Idioma nativo: {native_lang}, Inglés: {english_level}

Objetivo profesional: {primary_objective}
Intereses: {', '.join(interests) if interests else 'No especificados'}

Fortalezas: {', '.join(strengths) if strengths else 'No especificadas'}
Enfoque actual: {current_focus}

Estilo pedagógico preferido: {pedagogical_style}
Reglas de instrucción:
{chr(10).join(f'  - {rule}' for rule in instruction_rules) if instruction_rules else '  - No especificadas'}

Pensamiento crítico:
{chr(10).join(f'  - {item}' for item in critical_thinking) if critical_thinking else '  - No especificado'}
--- FIN PERFIL ---

INSTRUCCIONES ADICIONALES:
- Adapta tu lenguaje y nivel técnico según el perfil del usuario
- Prioriza el estilo pedagógico indicado ({pedagogical_style})
- Considera sus fortalezas y objetivos profesionales al responder
- Sigue las reglas de instrucción especificadas en el perfil
"""

    return base_prompt + profile_section


def get_user_profile() -> Optional[Dict]:
    """
    Obtiene el perfil del usuario (con cache).

    Función de conveniencia que retorna el perfil cargado, usando cache
    si está disponible. Equivalente a llamar `load_user_profile()` pero
    con nombre más semántico.

    Returns:
        Diccionario con el perfil del usuario o None si no está disponible.
    """
    return load_user_profile()


def clear_profile_cache() -> None:
    """
    Limpia el cache del perfil.

    Útil para testing o cuando se necesita recargar el perfil después
    de modificarlo en disco.
    """
    global _profile_cache
    _profile_cache = None
    logger.debug("Cache del perfil limpiado")
