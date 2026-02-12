"""
Extractor de Metadatos Estructurados - Sistema RAG Dialektos

Este módulo implementa la resolución híbrida de metadatos para documentos PDF.
Combina múltiples fuentes de información con un sistema de prioridades:

    1. Defaults globales (config YAML)
    2. Inferencia automática (carpeta, filename, metadata interna del PDF)
    3. Reglas de mapping (config YAML: folder→asignatura, filename→tipo)
    4. Overrides explícitos por archivo (config YAML, máxima prioridad)

Clase:
    MetadataExtractor: Resuelve metadatos estructurados para cada PDF

Autor: David Arroyo
Proyecto: Dialektos - Sistema RAG Adaptativo
"""

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pypdf import PdfReader

from .models import StructuredMetadata


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stopwords para detección de idioma por heurística
# ---------------------------------------------------------------------------
_STOPWORDS: Dict[str, set] = {
    "es": {
        "de", "la", "el", "en", "y", "los", "del", "las", "un", "por",
        "con", "una", "su", "para", "es", "al", "lo", "como", "más",
        "pero", "sus", "le", "ya", "se", "desde", "fue", "ha", "son",
        "entre", "está", "cuando", "muy", "sin", "sobre", "también",
        "me", "hasta", "hay", "donde", "quien", "después", "todo",
        "esta", "ser", "tiene", "nos", "ni", "otro", "ese", "cada",
    },
    "en": {
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
        "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
        "this", "but", "his", "by", "from", "they", "we", "say", "her",
        "she", "or", "an", "will", "my", "one", "all", "would", "there",
        "their", "what", "so", "up", "out", "if", "about", "who", "get",
        "which", "go", "when", "can", "no", "just", "him", "been", "has",
    },
    "fr": {
        "le", "de", "un", "être", "et", "à", "il", "avoir", "ne", "je",
        "son", "que", "se", "qui", "ce", "dans", "en", "du", "elle", "au",
        "pas", "pour", "sur", "par", "une", "avec", "tout", "faire",
        "mais", "comme", "ou", "nous", "vous", "leur", "bien", "entre",
    },
    "pt": {
        "de", "a", "o", "que", "e", "do", "da", "em", "um", "para",
        "é", "com", "não", "uma", "os", "no", "se", "na", "por", "mais",
        "as", "dos", "como", "mas", "foi", "ao", "ele", "das", "tem",
    },
}


class MetadataExtractor:
    """
    Resuelve metadatos estructurados para documentos PDF usando un
    enfoque híbrido: inferencia automática + configuración manual.
    
    El flujo de resolución sigue una cadena de prioridades donde cada
    nivel puede sobreescribir al anterior:
    
        defaults < inferencia < mapping < overrides
    
    Attributes:
        config_path: Ruta al archivo YAML de configuración
        config: Diccionario con la configuración cargada
    
    Example:
        >>> extractor = MetadataExtractor("config/metadata_config.yaml")
        >>> meta = extractor.resolve(
        ...     filename="Tema1_Teoria.pdf",
        ...     source_folder="Calculo",
        ...     pdf_path=Path("data/raw_pdfs/Calculo/Tema1_Teoria.pdf"),
        ...     text_sample="El cálculo diferencial estudia..."
        ... )
        >>> meta.asignatura
        'Cálculo'
        >>> meta.tipo
        'Teoría'
    """
    
    def __init__(self, config_path: Path | str = Path("config/metadata_config.yaml")):
        """
        Inicializa el extractor cargando la configuración YAML.
        
        Args:
            config_path: Ruta al archivo de configuración.
                         Si no existe, se usan valores vacíos por defecto.
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        logger.info(f"MetadataExtractor inicializado con config: {self.config_path}")
    
    # ======================================================================
    # Carga de configuración
    # ======================================================================
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Carga el archivo YAML de configuración.
        
        Returns:
            Diccionario con la configuración. Si el archivo no existe,
            retorna una estructura vacía para que el extractor siga
            funcionando solo con inferencia automática.
        """
        if not self.config_path.exists():
            logger.warning(
                f"Archivo de configuración no encontrado: {self.config_path}. "
                "Se usarán solo defaults e inferencia automática."
            )
            return {
                "defaults": {},
                "folder_to_asignatura": {},
                "filename_patterns": [],
                "file_overrides": {},
            }
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        
        # Garantizar que todas las secciones existan
        config.setdefault("defaults", {})
        config.setdefault("folder_to_asignatura", {})
        config.setdefault("filename_patterns", [])
        config.setdefault("file_overrides", {})
        
        n_overrides = len(config["file_overrides"])
        n_patterns = len(config["filename_patterns"])
        n_folders = len(config["folder_to_asignatura"])
        logger.info(
            f"   Config cargada: {n_overrides} overrides, "
            f"{n_patterns} patrones filename, {n_folders} mappings carpeta"
        )
        return config
    
    # ======================================================================
    # Inferencia automática
    # ======================================================================
    
    def _infer_from_folder(self, source_folder: str) -> Dict[str, str]:
        """
        Infiere la asignatura a partir de la carpeta de origen.
        
        Busca primero en el mapping del config; si no hay match,
        usa el nombre de la carpeta directamente (capitalizado).
        
        Args:
            source_folder: Carpeta relativa (ej: "Calculo", "root")
            
        Returns:
            Dict con los campos inferidos (puede estar vacío)
        """
        result: Dict[str, str] = {}
        folder_map = self.config.get("folder_to_asignatura", {})
        
        if source_folder in folder_map:
            mapped = folder_map[source_folder]
            if mapped is not None:  # null en YAML = no inferir
                result["asignatura"] = mapped
        elif source_folder != "root":
            # Fallback: usar el nombre de carpeta como asignatura
            result["asignatura"] = source_folder.replace("_", " ").title()
        
        return result
    
    def _infer_from_filename(self, filename: str) -> Dict[str, str]:
        """
        Infiere tipo y tema_especifico a partir del nombre del archivo.
        
        Aplica los patrones regex definidos en filename_patterns del config.
        El primer patrón que haga match determina el tipo.
        
        Args:
            filename: Nombre del archivo PDF (ej: "Tema1_Matrices_Teoria.pdf")
            
        Returns:
            Dict con los campos inferidos (puede estar vacío)
        """
        result: Dict[str, str] = {}
        patterns = self.config.get("filename_patterns", [])
        
        for rule in patterns:
            pattern = rule.get("pattern", "")
            if re.search(pattern, filename):
                if "tipo" in rule:
                    result["tipo"] = rule["tipo"]
                break  # Primer match gana
        
        # Intentar extraer tema_especifico del nombre del archivo
        # Patrón: buscar palabras significativas descartando prefijos comunes
        stem = Path(filename).stem  # Sin extensión
        # Eliminar prefijos numéricos tipo "Tema1_", "Cap02_", "T1_"
        cleaned = re.sub(r"^(?:Tema|Cap|T|Capitulo|Chapter|Ch)\s*\d+[\s_-]*", "", stem, flags=re.IGNORECASE)
        # Eliminar sufijos de tipo ya detectado
        cleaned = re.sub(r"[\s_-]*(Teoria|Theory|Ejercicios|Exercises|Examen|Exam)$", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip("_- ")
        
        if cleaned and cleaned != stem and len(cleaned) >= 3:
            result["tema_especifico"] = cleaned.replace("_", " ").title()
        
        return result
    
    def _extract_pdf_metadata(self, pdf_path: Path) -> Dict[str, str]:
        """
        Extrae metadatos de la metadata interna del PDF (XMP/Info dict).
        
        Intenta obtener fecha de creación y autor del documento usando
        las propiedades internas del PDF vía pypdf.
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            Dict con los campos extraídos (puede estar vacío)
        """
        result: Dict[str, str] = {}
        
        try:
            reader = PdfReader(str(pdf_path))
            meta = reader.metadata
            
            if meta is None:
                return result
            
            # Extraer autor
            author = meta.get("/Author") or meta.get("/author")
            if author and isinstance(author, str) and author.strip():
                result["autor"] = author.strip()
            
            # Extraer fecha (año de creación)
            creation_date = meta.get("/CreationDate") or meta.get("/creationdate")
            if creation_date and isinstance(creation_date, str):
                # Formato típico: D:20240115120000 o similar
                year_match = re.search(r"(\d{4})", str(creation_date))
                if year_match:
                    result["fecha"] = year_match.group(1)
            
        except Exception as e:
            logger.debug(f"No se pudo extraer metadata interna de {pdf_path.name}: {e}")
        
        return result
    
    def _detect_language(self, text_sample: str) -> Optional[str]:
        """
        Detecta el idioma del texto usando una heurística de stopwords.
        
        Cuenta la frecuencia de stopwords de cada idioma en el texto
        y retorna el idioma con mayor coincidencia. Es una heurística
        ligera que no requiere dependencias externas.
        
        Args:
            text_sample: Muestra de texto (idealmente primeras páginas)
            
        Returns:
            Código de idioma ISO 639-1 (ej: "es", "en") o None si
            no hay suficiente evidencia.
        """
        if not text_sample or len(text_sample) < 50:
            return None
        
        # Tokenizar: palabras en minúscula
        words = re.findall(r"\b[a-záéíóúüñàèìòùâêîôûäëïöü]+\b", text_sample.lower())
        
        if len(words) < 20:
            return None
        
        word_set = set(words)
        word_counter = Counter(words)
        
        scores: Dict[str, float] = {}
        for lang, stopwords in _STOPWORDS.items():
            # Contar cuántas stopwords del idioma aparecen
            matches = word_set & stopwords
            # Ponderar por frecuencia (las stopwords más frecuentes dan más peso)
            score = sum(word_counter[w] for w in matches)
            scores[lang] = score
        
        if not scores:
            return None
        
        best_lang = max(scores, key=scores.get)  # type: ignore[arg-type]
        best_score = scores[best_lang]
        
        # Umbral mínimo: al menos 5% de las palabras deben ser stopwords
        if best_score < len(words) * 0.05:
            return None
        
        return best_lang
    
    # ======================================================================
    # Resolución final (merge con prioridades)
    # ======================================================================
    
    def resolve(
        self,
        filename: str,
        source_folder: str,
        pdf_path: Optional[Path] = None,
        text_sample: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Resuelve los metadatos estructurados para un PDF aplicando la
        cadena de prioridades completa.
        
        El resultado es un diccionario con los campos de StructuredMetadata
        (sin page_number ni total_pages, que se añaden por página después).
        
        Prioridad (de menor a mayor, el último gana):
            1. defaults del config
            2. Inferencia automática (carpeta, filename, PDF metadata, idioma)
            3. Reglas de mapping del config (ya incluidas en inferencia)
            4. file_overrides del config
        
        Args:
            filename: Nombre del archivo PDF
            source_folder: Carpeta de origen relativa
            pdf_path: Ruta completa al PDF (para metadata interna)
            text_sample: Muestra de texto (para detección de idioma)
            
        Returns:
            Dict con los metadatos resueltos. Los campos que no se pudieron
            resolver tendrán valor None.
            
        Example:
            >>> result = extractor.resolve("Tema1.pdf", "Calculo")
            >>> result["asignatura"]
            'Cálculo'
        """
        # Nivel 1: Defaults globales
        resolved: Dict[str, Any] = {}
        defaults = self.config.get("defaults", {})
        for key, value in defaults.items():
            if value is not None:
                resolved[key] = value
        
        # Nivel 2: Inferencia automática
        # 2a. Carpeta → asignatura
        folder_inferred = self._infer_from_folder(source_folder)
        resolved.update(folder_inferred)
        
        # 2b. Filename → tipo, tema_especifico
        filename_inferred = self._infer_from_filename(filename)
        resolved.update(filename_inferred)
        
        # 2c. PDF metadata interna → fecha, autor
        if pdf_path is not None:
            pdf_inferred = self._extract_pdf_metadata(pdf_path)
            resolved.update(pdf_inferred)
        
        # 2d. Detección de idioma por heurística
        if text_sample is not None:
            detected_lang = self._detect_language(text_sample)
            if detected_lang is not None:
                resolved["idioma"] = detected_lang
        
        # Nivel 3: Overrides explícitos (máxima prioridad)
        overrides = self.config.get("file_overrides", {}).get(filename, {})
        if overrides:
            logger.debug(f"Aplicando overrides para {filename}: {list(overrides.keys())}")
            for key, value in overrides.items():
                if value is not None:
                    resolved[key] = value
        
        logger.info(
            f"Metadatos resueltos para {filename}: "
            f"asignatura={resolved.get('asignatura')}, "
            f"tipo={resolved.get('tipo')}, "
            f"idioma={resolved.get('idioma')}"
        )
        
        return resolved
