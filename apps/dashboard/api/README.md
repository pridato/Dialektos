# Dialektos API - Backend FastAPI

API REST para Dialektos que expone toda la lógica de negocio para que el frontend Next.js la consuma.

## Requisitos Previos

1. **Python** 3.10+
2. Todas las dependencias del proyecto principal instaladas (ver `requirements.txt` en la raíz)

## Instalación

```bash
# Desde el directorio raíz del proyecto
cd apps/dashboard/api

# Instalar dependencias de la API
pip install -r requirements.txt

# O instalar desde la raíz del proyecto (incluye todas las dependencias)
pip install -r ../../requirements.txt
pip install -r requirements.txt
```

## Configuración

Asegúrate de tener configurado:
- Variables de entorno (`.env` en la raíz del proyecto)
- Base de datos inicializada (`python -m src.bio.db`)
- ChromaDB configurado para RAG

## Ejecución

```bash
# Desde el directorio api/
python main.py

# O con uvicorn directamente
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en `http://localhost:8000`

## Documentación de la API

Una vez ejecutándose, puedes acceder a:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Endpoints Principales

### ICD y Biométricos
- `GET /api/icd/today` - Obtiene el ICD del día actual
- `GET /api/biometrics/today` - Datos biométricos de hoy
- `GET /api/biometrics/recent?days=14` - Datos de los últimos N días
- `POST /api/biometrics` - Guarda datos biométricos

### Sesiones de Estudio
- `GET /api/sessions/recent?limit=100` - Sesiones recientes
- `GET /api/sessions/streak` - Días con sesiones (últimos 28 días)

### Chat
- `POST /api/chat` - Procesa consulta RAG

### Analíticas
- `GET /api/analytics/correlation` - Datos para análisis de correlación

## CORS

La API está configurada para aceptar requests desde:
- `http://localhost:3000` (Next.js dev)
- `http://localhost:3001` (Next.js alternativo)

Para producción, actualiza `allow_origins` en `main.py`.

## Notas

- La API usa la misma base de datos y lógica que Streamlit
- Todos los modelos y funciones del proyecto principal están disponibles
- El sistema RAG (ChromaDB) debe estar inicializado antes de usar el chat
