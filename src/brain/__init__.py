"""
Módulo 2: Core Logic & Razonamiento (The Brain)

Este paquete contiene la lógica central del sistema Dialektos:
- Conexión con LLMs (GPT-4o mini)
- Retrieval System (búsqueda semántica → LLM)
- Memoria conversacional multi-turno
- Prompt Engineering y perfiles de usuario

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

from .llm_client import query_llm, query_llm_with_history
from .memory import ConversationMemory, ChatMessage
from .retriever import Retriever, RAGResponse, RetrievedChunk
from .adversary import (
    QuestionType,
    AdversaryState,
    QuestionAnalyzer,
    AdversaryPromptBuilder,
    AdversarySession,
)

__all__ = [
    "query_llm",
    "query_llm_with_history",
    "ConversationMemory",
    "ChatMessage",
    "Retriever",
    "RAGResponse",
    "RetrievedChunk",
    "QuestionType",
    "AdversaryState",
    "QuestionAnalyzer",
    "AdversaryPromptBuilder",
    "AdversarySession",
]
