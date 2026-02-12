"""
Módulo 2: Core Logic & Razonamiento (The Brain)

Este paquete contiene la lógica central del sistema Dialektos:
- Conexión con LLMs (GPT-4o mini)
- Retrieval System (búsqueda semántica → LLM)
- Prompt Engineering y perfiles de usuario

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

from .llm_client import query_llm

__all__ = ["query_llm"]
