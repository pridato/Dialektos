#!/bin/bash

# ============================================================================
# Script Ejecutor de Consultas SQL - Dialektos ChromaDB
# ============================================================================
# Este script ejecuta todas las consultas SQL secuencialmente y genera
# un reporte consolidado.

set -e  # Exit on error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuración
DB_PATH="data/chroma_db/chroma.sqlite3"
SQL_DIR="sql"
OUTPUT_DIR="sql/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="${OUTPUT_DIR}/report_${TIMESTAMP}.txt"

# Crear directorio de reportes si no existe
mkdir -p "${OUTPUT_DIR}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Análisis ChromaDB - Sistema RAG Dialektos              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verificar que existe la base de datos
if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}❌ Error: No se encontró la base de datos en ${DB_PATH}${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Base de datos encontrada: ${DB_PATH}${NC}"
echo -e "${GREEN}✅ Generando reporte en: ${REPORT_FILE}${NC}"
echo ""

# Iniciar reporte
cat > "${REPORT_FILE}" << EOF
═══════════════════════════════════════════════════════════════
  REPORTE DE ANÁLISIS CHROMADB - DIALEKTOS
═══════════════════════════════════════════════════════════════

Fecha de generación: $(date "+%Y-%m-%d %H:%M:%S")
Base de datos: ${DB_PATH}
Tamaño de BD: $(du -h "${DB_PATH}" | cut -f1)

═══════════════════════════════════════════════════════════════

EOF

# Lista de scripts SQL a ejecutar
SQL_SCRIPTS=(
    "01_inspect_schema.sql"
    "02_collection_stats.sql"
    "03_chunks_analysis.sql"
    "04_embeddings_quality.sql"
    "05_search_examples.sql"
)

# Ejecutar cada script
for script in "${SQL_SCRIPTS[@]}"; do
    script_path="${SQL_DIR}/${script}"
    
    if [ ! -f "$script_path" ]; then
        echo -e "${RED}❌ Script no encontrado: ${script}${NC}"
        continue
    fi
    
    echo -e "${YELLOW}▶ Ejecutando: ${script}${NC}"
    
    # Agregar al reporte
    echo "" >> "${REPORT_FILE}"
    echo "───────────────────────────────────────────────────────────" >> "${REPORT_FILE}"
    echo "  📄 ${script}" >> "${REPORT_FILE}"
    echo "───────────────────────────────────────────────────────────" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"
    
    # Ejecutar y agregar resultado al reporte
    sqlite3 "${DB_PATH}" < "${script_path}" >> "${REPORT_FILE}" 2>&1
    
    echo -e "${GREEN}  ✓ Completado${NC}"
    echo ""
done

# Finalizar reporte
echo "" >> "${REPORT_FILE}"
echo "═══════════════════════════════════════════════════════════════" >> "${REPORT_FILE}"
echo "  FIN DEL REPORTE" >> "${REPORT_FILE}"
echo "═══════════════════════════════════════════════════════════════" >> "${REPORT_FILE}"

echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Análisis completado exitosamente${NC}"
echo -e "${GREEN}📊 Reporte guardado en: ${REPORT_FILE}${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}💡 Para ver el reporte completo:${NC}"
echo -e "   cat ${REPORT_FILE}"
echo -e ""
echo -e "${BLUE}💡 O abrirlo con:${NC}"
echo -e "   less ${REPORT_FILE}"
echo ""

# También mostrar un resumen rápido en consola
echo -e "${YELLOW}═══ RESUMEN RÁPIDO ═══${NC}"
sqlite3 "${DB_PATH}" "SELECT COUNT(*) || ' chunks totales' FROM embeddings;"
sqlite3 "${DB_PATH}" "SELECT COUNT(DISTINCT metadata) || ' documentos únicos' FROM embeddings;"
sqlite3 "${DB_PATH}" "SELECT ROUND(AVG(LENGTH(document)), 2) || ' caracteres promedio por chunk' FROM embeddings;"
echo ""
