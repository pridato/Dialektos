"""
Limpieza de Texto - Sistema RAG Dialektos

Este módulo implementa transformaciones RegEx para corregir artefactos
introducidos por el formato PDF y preparar el texto para procesamiento NLP.

Clase:
    TextCleaner: Pipeline de limpieza de texto con métodos especializados

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import re
import logging
from typing import Optional


logger = logging.getLogger(__name__)


class TextCleaner:
    """
    Limpiador de texto especializado en artefactos de PDF.
    
    Este limpiador aplica una serie de transformaciones RegEx para
    corregir los artefactos introducidos por el formato PDF:
    
    - Arregla palabras cortadas con guiones al final de línea
    - Normaliza saltos de línea (mantiene párrafos reales)
    - Elimina ruido (espacios múltiples, caracteres invisibles)
    
    Example:
        >>> cleaner = TextCleaner()
        >>> clean_text = cleaner.clean_text(raw_pdf_text)
    """
    
    @staticmethod
    def fix_hyphenation(text: str) -> str:
        """
        Arregla palabras cortadas con guiones al final de línea.
        
        Problema:
            En un PDF, si "Algoritmo" no cabe en una línea:
            "Algo-\nritmo" → La IA lee dos palabras sin sentido
        
        Solución:
            Detecta el patrón [Guion] + [Salto de Línea] y lo elimina
        
        Args:
            text: Texto con posibles guiones de separación
            
        Returns:
            Texto con palabras unidas correctamente
            
        Example:
            >>> TextCleaner.fix_hyphenation("Algo-\nritmo")
            'Algoritmo'
        """
        # Patrón: guion seguido de salto de línea (puede haber espacios)
        pattern = r'-\s*\n\s*'
        cleaned = re.sub(pattern, '', text)
        
        logger.debug(f"Hyphenation fix: {len(re.findall(pattern, text))} correcciones aplicadas")
        return cleaned
    
    
    @staticmethod
    def normalize_line_breaks(text: str) -> str:
        """
        Normaliza saltos de línea respetando párrafos reales.
        
        Problema:
            Los PDFs ponen '\n' al final de cada línea visual.
            Para una máquina, eso parece el fin de una frase.
        
        Solución:
            - Saltos de línea simples (\n) → espacio en blanco
            - Saltos de línea dobles (\n\n) → mantener (indican cambio de párrafo)
        
        Args:
            text: Texto con saltos de línea arbitrarios
            
        Returns:
            Texto con frases continuas y párrafos preservados
        """
        # Primero, proteger los saltos dobles (párrafos reales)
        text = re.sub(r'\n\n+', '<<PARAGRAPH>>', text)
        
        # Reemplazar saltos simples por espacios
        text = re.sub(r'\n', ' ', text)
        
        # Restaurar los párrafos reales
        text = re.sub(r'<<PARAGRAPH>>', '\n\n', text)
        
        return text
    
    
    @staticmethod
    def remove_noise(text: str) -> str:
        """
        Elimina ruido: espacios múltiples, tabulaciones, caracteres invisibles.
        
        Problema:
            Dobles espacios, tabs, caracteres de control residuales.
        
        Solución:
            Colapsar cualquier secuencia de espacios en blanco en un solo espacio.
        
        Args:
            text: Texto con posible ruido
            
        Returns:
            Texto con espaciado normalizado
        """
        # Reemplazar múltiples espacios (incluyendo tabs) por un solo espacio
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Eliminar espacios al inicio y final de cada línea
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Eliminar más de dos saltos de línea consecutivos
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    
    @classmethod
    def clean_text(cls, raw_text: str) -> str:
        """
        Pipeline completo de limpieza de texto.
        
        Aplica las tres etapas de limpieza en orden:
            1. Arreglar guiones (hyphenation)
            2. Normalizar saltos de línea
            3. Eliminar ruido
        
        Args:
            raw_text: Texto extraído directamente del PDF
            
        Returns:
            Texto limpio y continuo, listo para procesamiento NLP
            
        Example:
            >>> cleaner = TextCleaner()
            >>> clean = cleaner.clean_text(pdf_text)
        """
        logger.debug("Iniciando pipeline de limpieza")
        
        # Etapa A: Hyphenation
        text = cls.fix_hyphenation(raw_text)
        
        # Etapa B: Line Breaks
        text = cls.normalize_line_breaks(text)
        
        # Etapa C: Noise Reduction
        text = cls.remove_noise(text)
        
        logger.debug(f"Limpieza completada. Longitud final: {len(text)} caracteres")
        return text
