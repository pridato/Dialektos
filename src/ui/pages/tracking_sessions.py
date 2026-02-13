"""
Página: Tracking de Sesiones de Estudio (Wrapper)

Este módulo es un wrapper que re-exporta la función render desde session_tracking.py
para mantener compatibilidad con el enrutamiento en app.py.

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

from src.ui.pages.session_tracking import render_session_tracking


def render(engine) -> None:
    """
    Renderiza la página de Tracking de Sesiones.
    
    Wrapper que llama a render_session_tracking para mantener
    compatibilidad con el enrutamiento en app.py.
    """
    render_session_tracking(engine)
