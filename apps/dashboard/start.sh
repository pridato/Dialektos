#!/bin/bash

# Script para iniciar tanto el backend como el frontend

echo "🚀 Iniciando Dialektos Dashboard..."

# Verificar que estamos en el directorio correcto
if [ ! -f "package.json" ]; then
    echo "❌ Error: No se encontró package.json. Ejecuta este script desde apps/dashboard/"
    exit 1
fi

# Verificar que existe el directorio api
if [ ! -d "api" ]; then
    echo "❌ Error: No se encontró el directorio api/"
    exit 1
fi

# Detectar y activar el entorno virtual de Python
VENV_PATH="../../venv"
if [ -d "$VENV_PATH" ]; then
    echo "🔧 Activando entorno virtual..."
    source "$VENV_PATH/bin/activate"
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    echo "⚠️  Usando python3 del sistema (recomendado: usar entorno virtual)"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: No se encontró Python. Instala Python 3.11+ o activa el entorno virtual."
    exit 1
fi

# Función para limpiar procesos al salir
cleanup() {
    echo ""
    echo "🛑 Deteniendo servidores..."
    kill $API_PID $FRONTEND_PID 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

# Obtener la ruta absoluta de la raíz del proyecto (dos niveles arriba desde apps/dashboard)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Iniciar API en background
echo "📡 Iniciando API FastAPI..."
echo "   PYTHONPATH: $PROJECT_ROOT"
cd api
$PYTHON_CMD main.py &
API_PID=$!
cd ..

# Esperar un poco para que la API inicie
sleep 3

# Verificar que la API está corriendo
if ! curl -s http://localhost:8000/ > /dev/null; then
    echo "⚠️  Advertencia: La API no responde en http://localhost:8000"
    echo "   Asegúrate de que todas las dependencias estén instaladas"
fi

# Iniciar frontend
echo "🎨 Iniciando frontend Next.js..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Servidores iniciados:"
echo "   📡 API: http://localhost:8000"
echo "   🎨 Frontend: http://localhost:3000"
echo ""
echo "Presiona Ctrl+C para detener ambos servidores"

# Esperar a que termine cualquiera de los procesos
wait
