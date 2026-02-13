# Dialektos Dashboard - Frontend Next.js

Frontend moderno para Dialektos construido con Next.js, React y shadcn/ui.

## Arquitectura

Este proyecto es el frontend que consume la API REST de Python (FastAPI). La arquitectura es:

```
┌─────────────────┐
│  Next.js (UI)   │  ← Este proyecto
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│  FastAPI (API)  │  ← Backend Python
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SQLite + RAG   │  ← Datos y lógica de negocio
└─────────────────┘
```

## Requisitos Previos

1. **Node.js** 18+ y npm/pnpm/yarn
2. **Backend Python** ejecutándose (ver `api/README.md`)

## Instalación

```bash
# Instalar dependencias
npm install
# o
pnpm install
# o
yarn install
```

## Configuración

1. Copia el archivo de ejemplo de variables de entorno:
```bash
cp .env.example .env.local
```

2. Edita `.env.local` y configura la URL de la API:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Desarrollo

```bash
# Iniciar servidor de desarrollo
npm run dev
# o
pnpm dev
# o
yarn dev
```

El dashboard estará disponible en `http://localhost:3000`

## Estructura del Proyecto

```
apps/dashboard/
├── app/                    # Páginas Next.js (App Router)
│   ├── page.tsx           # Página principal
│   ├── layout.tsx         # Layout global
│   └── globals.css        # Estilos globales
├── components/            # Componentes React
│   └── ui/                # Componentes shadcn/ui
├── hooks/                 # Custom React hooks
│   ├── use-icd.ts         # Hook para datos del ICD
│   ├── use-biometrics.ts  # Hook para datos biométricos
│   └── use-chat.ts        # Hook para chat
├── lib/                   # Utilidades
│   └── api.ts             # Cliente API
└── api/                   # Backend Python (FastAPI)
    └── main.py            # API REST
```

## Características

- ✅ Dashboard con ICD en tiempo real
- ✅ Chat Socrático con RAG
- ✅ Bio-Tracker para registrar datos
- ✅ Analíticas y correlaciones
- ✅ Diseño responsive (mobile-first)
- ✅ Tema oscuro integrado

## Scripts Disponibles

- `npm run dev` - Inicia servidor de desarrollo
- `npm run build` - Construye para producción
- `npm run start` - Inicia servidor de producción
- `npm run lint` - Ejecuta el linter

## Notas

- El frontend requiere que el backend Python esté ejecutándose
- Asegúrate de que CORS esté configurado correctamente en el backend
- Las variables de entorno con `NEXT_PUBLIC_` son accesibles en el cliente
