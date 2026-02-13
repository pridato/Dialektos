"""
API REST para Dialektos - Backend FastAPI

Expone endpoints para que el frontend Next.js consuma toda la lógica de negocio.
Mantiene toda la funcionalidad existente de Streamlit pero como API REST.

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations
from src.bio.models import DailyBiometrics, DailyConfounders, StudySession, MoodEnum, ExerciseTypeEnum
from src.bio.decision import get_strategy, get_strategy_for_record
from src.bio.db import get_engine
from src.bio.dao import create_or_update_biometrics
from sqlmodel import Session, select
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from typing import Any, Dict, List, Optional
from datetime import date, datetime, timedelta

import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al PYTHONPATH
# Desde apps/dashboard/api/main.py necesitamos subir 4 niveles para llegar a la raíz
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


app = FastAPI(title="Dialektos API", version="1.0.0")

# CORS - Permitir requests desde Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "http://localhost:3001"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# MODELOS PYDANTIC PARA REQUEST/RESPONSE
# ============================================================================


class ICDResponse(BaseModel):
    icd_score: Optional[float]
    zone: Optional[str]
    zone_label: Optional[str]
    zone_color: Optional[str]
    strategy: Optional[Dict[str, Any]]


class BiometricData(BaseModel):
    date: date
    # Objetivos
    hrv_rmssd: Optional[float] = None
    resting_hr: Optional[int] = None
    avg_hr_sleep: Optional[float] = None
    sleep_total_min: Optional[int] = None
    deep_sleep_min: Optional[int] = None
    rem_sleep_min: Optional[int] = None
    light_sleep_min: Optional[int] = None
    awake_min: Optional[int] = None
    sleep_start_time: Optional[str] = None
    sleep_quality: Optional[int] = None
    body_resources: Optional[int] = None
    training_load: Optional[float] = None
    # Subjetivos
    energy_level: Optional[int] = None
    mental_clarity: Optional[int] = None
    mood: Optional[str] = None
    motivation: Optional[int] = None
    muscle_soreness: Optional[int] = None


class ConfounderData(BaseModel):
    date: date
    caffeine_mg: Optional[int] = None
    screen_time_pre_sleep: Optional[int] = None
    meals_quality: Optional[int] = None
    social_stress: Optional[int] = None
    exercise_type: Optional[str] = None
    exercise_min: Optional[int] = None
    notes: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    adversary_info: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    prompt: str
    adversary_mode: bool = True
    session_id: Optional[str] = None  # Si se envía, se persiste memoria en Redis


class ChatResponse(BaseModel):
    answer: str
    sources: Optional[List[Dict[str, Any]]] = None
    adversary_info: Optional[Dict[str, Any]] = None


class StudySessionCreate(BaseModel):
    """Payload del HUD al finalizar sesión (guardar en SQLite)."""
    start_time: str
    end_time: str
    duration_minutes: int
    subject: str
    task_type: str  # deep_work, active_recall, superficial
    goal_description: str
    distraction_count: int = 0
    perceived_focus_score: int  # 1-10
    perceived_difficulty: int  # 1-5
    date_ref: str  # YYYY-MM-DD
    pre_session_energy: Optional[int] = None
    zone: Optional[str] = None
    comments: Optional[str] = None


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Dialektos API", "status": "ok"}


# Cache-aside: clave y TTL para ICD del día
ICD_CACHE_KEY = "api:icd:today"
ICD_CACHE_TTL_SECONDS = 300  # 5 minutos


def _icd_response_to_dict(resp: ICDResponse) -> Dict[str, Any]:
    return resp.model_dump()


@app.get("/api/icd/today", response_model=ICDResponse)
async def get_today_icd():
    """Obtiene el ICD del día actual (cache-aside con Redis)."""
    import json
    from src.cache.redis_client import get_redis

    r = get_redis(use_async=True)
    try:
        cached_icd = await r.get(ICD_CACHE_KEY)
        if cached_icd:
            return ICDResponse(**json.loads(cached_icd))
    except Exception:
        pass

    engine = get_engine()
    with Session(engine) as db_session:
        today = date.today()
        stmt = select(DailyBiometrics).where(DailyBiometrics.date == today)
        record = db_session.exec(stmt).first()

        if record is None or record.icd_score is None:
            out = ICDResponse(
                icd_score=None,
                zone=None,
                zone_label=None,
                zone_color=None,
                strategy=None,
            )
            return out

        strategy = get_strategy(record.icd_score)
        out = ICDResponse(
            icd_score=record.icd_score,
            zone=strategy.zone.value,
            zone_label=strategy.name,
            zone_color=strategy.color,
            strategy={
                "name": strategy.name,
                "emoji": strategy.emoji,
                "description": strategy.description,
                "ai_mode": strategy.ai_mode.value,
                "max_difficulty": strategy.max_difficulty.value,
                "recommended_tasks": [t.value for t in strategy.recommended_tasks],
            },
        )
        try:
            await r.setex(
                ICD_CACHE_KEY,
                ICD_CACHE_TTL_SECONDS,
                json.dumps(_icd_response_to_dict(out)),
            )
        except Exception:
            pass
        return out


@app.get("/api/biometrics/today")
async def get_today_biometrics():
    """Obtiene los datos biométricos del día actual."""
    engine = get_engine()
    with Session(engine) as session:
        today = date.today()
        stmt = select(DailyBiometrics).where(DailyBiometrics.date == today)
        record = session.exec(stmt).first()

        if record is None:
            return None

        return {
            "hrv_rmssd": record.hrv_rmssd,
            "ln_rmssd": record.ln_rmssd,
            "hrv_baseline_7d": record.hrv_baseline_7d,
            "sleep_quality": record.sleep_quality,
            "sleep_total_min": record.sleep_total_min,
            "deep_sleep_min": record.deep_sleep_min,
            "rem_sleep_min": record.rem_sleep_min,
            "light_sleep_min": record.light_sleep_min,
            "body_resources": record.body_resources,
            "energy_level": record.energy_level,
            "mental_clarity": record.mental_clarity,
            "sleep_consistency": record.sleep_consistency,
        }


@app.get("/api/biometrics/recent")
async def get_recent_biometrics(days: int = 14):
    """Obtiene los datos biométricos de los últimos N días."""
    engine = get_engine()
    with Session(engine) as session:
        cutoff = date.today() - timedelta(days=days)
        stmt = (
            select(DailyBiometrics)
            .where(DailyBiometrics.date >= cutoff)
            .order_by(DailyBiometrics.date.asc())
        )
        records = session.exec(stmt).all()

        return [
            {
                "date": r.date.isoformat(),
                "icd_score": r.icd_score,
                "hrv_rmssd": r.hrv_rmssd,
                "resting_hr": r.resting_hr,
                "sleep_quality": r.sleep_quality,
                "body_resources": r.body_resources,
                "training_load": r.training_load,
            }
            for r in records
        ]


@app.get("/api/sessions/recent")
async def get_recent_sessions(limit: int = 100):
    """Obtiene las sesiones de estudio más recientes."""
    engine = get_engine()
    with Session(engine) as session:
        stmt = (
            select(StudySession)
            .order_by(StudySession.date.desc(), StudySession.start_time.desc())
            .limit(limit)
        )
        sessions = session.exec(stmt).all()

        return [
            {
                "date": s.date.isoformat(),
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "duration_min": s.duration_min,
                "task_type": s.task_type,
                "focus_score": s.focus_score,
            }
            for s in sessions
        ]


@app.get("/api/sessions/streak")
async def get_study_streak():
    """Obtiene los días con sesiones de estudio (últimos 28 días)."""
    engine = get_engine()
    with Session(engine) as session:
        cutoff = date.today() - timedelta(days=28)
        stmt = select(StudySession).where(StudySession.date >= cutoff)
        sessions = session.exec(stmt).all()

        # Obtener días únicos con sesiones
        days_with_sessions = set(s.date for s in sessions)

        return {
            "days": [d.isoformat() for d in days_with_sessions],
        }


def _map_task_category_to_type(category: str) -> str:
    """Mapea task_category del HUD al TaskTypeEnum existente."""
    m = {"deep_work": "theory_new",
         "active_recall": "coding", "superficial": "review"}
    return m.get(category, "theory_new")


def _map_difficulty_1_5_to_attempted(d: int) -> str:
    """Mapea dificultad 1-5 a EASY/MEDIUM/HARD/EPIC."""
    if d <= 2:
        return "EASY"
    if d == 3:
        return "MEDIUM"
    if d == 4:
        return "HARD"
    return "EPIC"


@app.post("/api/sessions")
async def save_study_session(data: StudySessionCreate):
    """Guarda una sesión de estudio desde el HUD en SQLite (metrics.db)."""
    engine = get_engine()
    date_ref = date.fromisoformat(data.date_ref)

    with Session(engine) as db_session:
        try:
            # Asegurar que exista fila en daily_biometrics para la FK
            create_or_update_biometrics(db_session, {"date": date_ref})

            start_dt = datetime.fromisoformat(
                data.start_time.replace("Z", "+00:00")
            ).replace(tzinfo=None)
            end_dt = datetime.fromisoformat(
                data.end_time.replace("Z", "+00:00")
            ).replace(tzinfo=None)

            record = StudySession(
                date=date_ref,
                start_time=start_dt,
                end_time=end_dt,
                duration_min=data.duration_minutes,
                task_type=_map_task_category_to_type(data.task_type),
                task_category=data.task_type,
                difficulty_attempted=_map_difficulty_1_5_to_attempted(
                    data.perceived_difficulty
                ),
                focus_score=data.perceived_focus_score,
                perceived_difficulty=data.perceived_difficulty,
                interruptions=data.distraction_count,
                subject=data.subject,
                goal_description=data.goal_description,
                comments=data.comments,
                pre_session_energy=data.pre_session_energy,
                zone=data.zone,
            )
            db_session.add(record)
            db_session.commit()
            db_session.refresh(record)
            return {
                "success": True,
                "session_id": record.session_id,
            }
        except Exception as e:
            db_session.rollback()
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/biometrics")
async def save_biometrics(data: BiometricData):
    """Guarda o actualiza datos biométricos para una fecha. Invalida caché ICD del día."""
    engine = get_engine()
    with Session(engine) as session:
        try:
            bio_dict = data.model_dump()
            record = create_or_update_biometrics(session, bio_dict)
            session.commit()

            # Invalidar caché ICD para que la próxima lectura refleje los nuevos datos
            try:
                from src.cache.redis_client import get_redis
                r = get_redis(use_async=True)
                await r.delete(ICD_CACHE_KEY)
            except Exception:
                pass

            strategy = None
            if record.icd_score is not None:
                strat = get_strategy(record.icd_score)
                strategy = {
                    "name": strat.name,
                    "emoji": strat.emoji,
                    "description": strat.description,
                    "icd_score": record.icd_score,
                }

            return {
                "success": True,
                "icd_score": record.icd_score,
                "strategy": strategy,
            }
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/confounders")
async def save_confounders(data: ConfounderData):
    """Guarda o actualiza variables de confusión para una fecha."""
    engine = get_engine()
    with Session(engine) as session:
        try:
            stmt = select(DailyConfounders).where(
                DailyConfounders.date == data.date)
            existing = session.exec(stmt).first()

            conf_dict = data.model_dump(exclude_none=True)
            if existing:
                for key, value in conf_dict.items():
                    setattr(existing, key, value)
            else:
                new_conf = DailyConfounders(**conf_dict)
                session.add(new_conf)

            session.commit()
            return {"success": True}
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Procesa una consulta de chat usando el sistema RAG. Con session_id persiste memoria en Redis."""
    try:
        from src.brain.retriever import Retriever
        from src.ingest.chroma_persistence import ChromaDBPersistence
        from src.cache.redis_client import get_redis

        db = ChromaDBPersistence()
        semantic_cache = None
        try:
            from src.cache.rag_semantic_cache import RagSemanticCache
            semantic_cache = RagSemanticCache(db=db, redis_client=get_redis())
        except Exception:
            pass

        session_memory = None
        initial_messages: Optional[List[Dict[str, str]]] = None
        if request.session_id:
            try:
                from src.cache.session_memory import RedisSessionMemory
                session_memory = RedisSessionMemory(redis_client=get_redis())
                initial_messages = session_memory.get(request.session_id)
            except Exception:
                pass

        retriever = Retriever(
            db=db,
            initial_messages=initial_messages,
            semantic_cache=semantic_cache,
        )
        response = retriever.retrieve_and_query(
            request.prompt,
            adversary_mode=request.adversary_mode,
        )

        if request.session_id and session_memory:
            try:
                session_memory.set_messages(
                    request.session_id,
                    retriever.memory.get_messages(),
                )
            except Exception:
                pass

        sources_data = []
        if response.source_type == "notes" and response.sources:
            for src in response.sources:
                sources_data.append({
                    "type": "notes",
                    "filename": src.metadata.get("filename", "?"),
                    "page": src.metadata.get("page_number", "?"),
                    "score": src.score,
                })
        elif response.source_type == "web" and response.web_sources:
            for src in response.web_sources:
                sources_data.append({
                    "type": "web",
                    "title": src.title,
                    "url": src.url,
                    "score": src.score,
                })

        adversary_info = {
            "question_type": response.question_type.value if response.question_type else None,
            "active": response.adversary_activated,
            "depth": response.adversary_depth,
        }

        return ChatResponse(
            answer=response.answer,
            sources=sources_data if sources_data else None,
            adversary_info=adversary_info,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en chat: {str(e)}")


@app.get("/api/analytics/correlation")
async def get_correlation_data():
    """Obtiene datos para análisis de correlación."""
    try:
        from src.bio.analysis import load_analysis_dataframe

        engine = get_engine()
        df = load_analysis_dataframe(engine)

        if df.empty:
            return {"data": [], "message": "No hay datos suficientes"}

        # Preparar datos para scatter plot VFC vs Focus
        scatter_data = []
        if "ln_rmssd" in df.columns and "focus_score_mean" in df.columns:
            for _, row in df.dropna(subset=["ln_rmssd", "focus_score_mean"]).iterrows():
                scatter_data.append({
                    "vfc": row["ln_rmssd"],
                    "foco": row["focus_score_mean"],
                    "date": row["date"].isoformat() if "date" in row else None,
                })

        # Matriz de correlación
        correlation_matrix = []
        if "ln_rmssd" in df.columns and "focus_score_mean" in df.columns:
            corr_cols = ["ln_rmssd", "sleep_quality",
                         "energy_level", "focus_score_mean"]
            available_cols = [c for c in corr_cols if c in df.columns]
            if len(available_cols) > 1:
                corr_df = df[available_cols].corr()
                for idx, row in corr_df.iterrows():
                    correlation_matrix.append({
                        "metric": idx,
                        **{col: row[col] for col in corr_df.columns},
                    })

        return {
            "scatter_data": scatter_data,
            "correlation_matrix": correlation_matrix,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error en análisis: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
