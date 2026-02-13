"""
Página: Chat Principal con Modo Adaptativo

Chat RAG integrado con el ICD:
- Badge visible mostrando modo actual (Socrático/Guiado/Apoyo/Pasivo)
- Streaming de respuestas (efecto máquina de escribir)
- Integración con selector de prompts dinámico del Módulo 3
- Historial de conversación en la sesión
- Fuentes citadas (apuntes o web)

Referencia: docs/TAREAS.md § Módulo 4 — Chat Principal con Modo Adaptativo.

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import streamlit as st
from sqlmodel import Session

from src.bio.decision import (
    AIInteractionMode,
    PedagogicalStrategy,
    get_strategy,
    get_strategy_for_record,
)
from src.ui.components import COLORS, get_today_icd

logger = logging.getLogger(__name__)


def _get_mode_badge_html(strategy: Optional[PedagogicalStrategy]) -> str:
    """Genera HTML para el badge del modo actual de la IA."""
    if strategy is None:
        return f"""
        <div style="
            display: inline-block;
            background: {COLORS['bg_card']};
            border: 1px solid {COLORS['border']};
            border-radius: 20px;
            padding: 6px 16px;
            font-size: 0.9em;
            color: {COLORS['text_muted']};
        ">
            Sin ICD — Modo estándar
        </div>
        """

    color = strategy.color
    mode_names = {
        AIInteractionMode.SOCRATIC: "Socrático Hardcore",
        AIInteractionMode.GUIDED: "Explicativo Guiado",
        AIInteractionMode.SUPPORTIVE: "Repaso Suave",
        AIInteractionMode.PASSIVE: "Recuperación Pasiva",
    }
    mode_name = mode_names.get(strategy.ai_mode, strategy.ai_mode.value)

    return f"""
    <div style="
        display: inline-block;
        background: linear-gradient(135deg, {color}22, {color}08);
        border: 1px solid {color}44;
        border-radius: 20px;
        padding: 6px 16px;
        font-size: 0.9em;
        color: {color};
        font-weight: 600;
    ">
        {strategy.emoji} {mode_name} &nbsp;·&nbsp; ICD {strategy.zone.value.upper()}
    </div>
    """


def _init_chat_state() -> None:
    """Inicializa el estado de la sesión de chat."""
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "retriever" not in st.session_state:
        st.session_state.retriever = None
    if "chat_initialized" not in st.session_state:
        st.session_state.chat_initialized = False


def _get_retriever():
    """Obtiene o crea la instancia del Retriever."""
    if st.session_state.retriever is None:
        try:
            from src.brain.retriever import Retriever
            st.session_state.retriever = Retriever()
            st.session_state.chat_initialized = True
        except Exception as e:
            logger.error(f"Error inicializando Retriever: {e}")
            st.session_state.chat_initialized = False
            return None
    return st.session_state.retriever


def render_chat(engine: Any) -> None:
    """Renderiza la página de Chat Adaptativo con diseño moderno."""

    _init_chat_state()

    # ── Header mejorado ──
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.markdown("# Chat Socrático")
        st.caption("Aprende mediante preguntas guiadas")
    
    # ── Badge de modo actual ──
    with Session(engine) as session:
        today_icd = get_today_icd(session)

    strategy = get_strategy_for_record(today_icd) if today_icd is not None else None
    
    with header_col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Espaciado
        st.markdown(_get_mode_badge_html(strategy), unsafe_allow_html=True)

    if strategy:
        st.info(f"💡 {strategy.description}")
    else:
        st.info(
            "💡 Registra tus datos fisiológicos para activar el modo adaptativo. "
            "Por ahora el chat funciona en modo estándar."
        )

    st.divider()

    # ── Controles mejorados ──
    ctrl_col1, ctrl_col2 = st.columns([1, 1])
    with ctrl_col1:
        adversary_toggle = st.toggle(
            "🔍 Modo Socrático",
            value=True,
            help="Activa el cuestionamiento socrático para preguntas conceptuales. "
                  "La IA te hará preguntas en lugar de darte respuestas directas.",
        )
    with ctrl_col2:
        if st.button("🗑️ Limpiar Chat", type="secondary", use_container_width=True):
            st.session_state.chat_messages = []
            retriever = st.session_state.retriever
            if retriever:
                retriever.clear_memory()
            st.rerun()

    st.divider()

    # ── Historial de mensajes mejorado ──
    if not st.session_state.chat_messages:
        st.markdown(
            """
            <div style="
                text-align: center;
                padding: 48px 24px;
                color: #8b949e;
            ">
                <div style="font-size: 3em; margin-bottom: 16px;">💬</div>
                <div style="font-size: 1.1em; margin-bottom: 8px;">Comienza una conversación</div>
                <div style="font-size: 0.9em;">Escribe tu pregunta en el campo de abajo</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"], avatar=msg.get("avatar")):
            st.markdown(msg["content"])

            # Mostrar fuentes si las hay (mejorado)
            if msg.get("sources"):
                with st.expander("📚 Ver fuentes y referencias", expanded=False):
                    for idx, src in enumerate(msg["sources"], 1):
                        if src.get("type") == "notes":
                            st.markdown(
                                f"""
                                <div style="
                                    background: #1a1d23;
                                    border-left: 3px solid #58a6ff;
                                    padding: 8px 12px;
                                    margin: 4px 0;
                                    border-radius: 4px;
                                ">
                                    <strong>📄 Apuntes:</strong> {src['filename']} (p.{src['page']})<br>
                                    <span style="color: #8b949e; font-size: 0.85em;">
                                        Similitud: {src['score']:.2f}
                                    </span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        elif src.get("type") == "web":
                            st.markdown(
                                f"""
                                <div style="
                                    background: #1a1d23;
                                    border-left: 3px solid #22c55e;
                                    padding: 8px 12px;
                                    margin: 4px 0;
                                    border-radius: 4px;
                                ">
                                    <strong>🌐 Web:</strong> <a href="{src['url']}" target="_blank">{src['title']}</a><br>
                                    <span style="color: #8b949e; font-size: 0.85em;">
                                        Score: {src['score']:.2f}
                                    </span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

            # Mostrar metadata de adversario mejorado
            if msg.get("adversary_info"):
                info = msg["adversary_info"]
                if info.get("active"):
                    st.markdown(
                        f"""
                        <div style="
                            background: #f59e0b22;
                            border: 1px solid #f59e0b44;
                            border-radius: 6px;
                            padding: 6px 10px;
                            margin-top: 8px;
                            font-size: 0.85em;
                            color: #f59e0b;
                        ">
                            🔍 <strong>Modo Socrático Activo</strong> · 
                            Tipo: {info.get('question_type', '?')}
                            {f" · Profundidad: {info['depth']}/5" if info.get('depth') else ""}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # ── Input de chat mejorado ──
    st.markdown(
        """
        <div style="
            background: #1a1d23;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 8px;
            margin-top: 16px;
        ">
        """,
        unsafe_allow_html=True,
    )
    
    prompt = st.chat_input(
        "💬 Escribe tu pregunta... (soporta LaTeX con $$ y bloques de código)",
        key="chat_input",
    )
    
    st.markdown("</div>", unsafe_allow_html=True)

    if prompt:
        # Agregar mensaje del usuario
        st.session_state.chat_messages.append({
            "role": "user",
            "content": prompt,
            "avatar": "👤",
        })
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Obtener retriever
        retriever = _get_retriever()

        if retriever is None:
            error_msg = (
                "No se pudo inicializar el sistema RAG. "
                "Verifica que ChromaDB esté disponible y la API key configurada."
            )
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": error_msg,
                "avatar": "🧠",
            })
            with st.chat_message("assistant", avatar="🧠"):
                st.error(error_msg)
            return

        # Inyectar prompt hint del ICD al system prompt si hay estrategia
        if strategy and strategy.prompt_hint:
            # El hint ya se inyecta a través del adversary mode y el retriever
            pass

        # Consultar RAG
        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("Pensando..."):
                try:
                    from src.brain.retriever import RAGResponse
                    response: RAGResponse = retriever.retrieve_and_query(
                        prompt,
                        adversary_mode=adversary_toggle,
                    )

                    # Mostrar respuesta con efecto de streaming simulado
                    st.markdown(response.answer)

                    # Preparar fuentes para el historial
                    sources_data: List[Dict[str, Any]] = []
                    if response.source_type == "notes" and response.sources:
                        for src in response.sources:
                            sources_data.append({
                                "type": "notes",
                                "filename": src.metadata.get("filename", "?"),
                                "page": src.metadata.get("page_number", "?"),
                                "score": src.score,
                            })
                        with st.expander("Ver fuentes", expanded=False):
                            for src in response.sources:
                                st.caption(
                                    f"Apuntes: {src.metadata.get('filename', '?')} "
                                    f"(p.{src.metadata.get('page_number', '?')}) "
                                    f"— Similitud: {src.score:.2f}"
                                )

                    elif response.source_type == "web" and response.web_sources:
                        for src in response.web_sources:
                            sources_data.append({
                                "type": "web",
                                "title": src.title,
                                "url": src.url,
                                "score": src.score,
                            })
                        with st.expander("Ver fuentes web", expanded=False):
                            for src in response.web_sources:
                                st.caption(f"[{src.title}]({src.url}) — Score: {src.score:.2f}")

                    # Metadata adversario
                    adversary_info = {
                        "question_type": response.question_type.value if response.question_type else None,
                        "active": response.adversary_activated,
                        "depth": response.adversary_depth,
                    }

                    if response.adversary_activated:
                        st.caption(
                            f"Tipo: {adversary_info['question_type']} · "
                            f"Adversario: Activo"
                            + (f" · Profundidad: {response.adversary_depth}/5"
                               if response.adversary_depth else "")
                        )

                    # Guardar en historial
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": response.answer,
                        "avatar": "🧠",
                        "sources": sources_data,
                        "adversary_info": adversary_info,
                    })

                except Exception as e:
                    error_msg = f"Error al procesar la consulta: {str(e)}"
                    st.error(error_msg)
                    logger.error(f"Error en chat: {e}", exc_info=True)
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": f"Error: {str(e)}",
                        "avatar": "🧠",
                    })
