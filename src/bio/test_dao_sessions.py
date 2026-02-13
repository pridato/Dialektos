"""
Tests unitarios para el DAO de StudySession — Tarea 3.6.1.

Verifican:
- Captura automática de icd_at_start desde DailyBiometrics.
- Funcionamiento cuando no hay DailyBiometrics (icd_at_start = None).
- Múltiples sesiones por día.
- Filtrado por fecha y ventana temporal.

Uso:
    pytest src/bio/test_dao_sessions.py -v

Autor: David Arroyo
Proyecto: Dialektos
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.bio.dao import (
    create_study_session,
    get_recent_sessions,
    get_sessions_by_date,
)
from src.bio.models import DailyBiometrics, StudySession


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    """Motor SQLite en memoria con tablas creadas."""
    eng = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture
def db_session(engine):
    """Sesión de base de datos limpia para cada test."""
    with Session(engine) as session:
        yield session


def _seed_biometrics(
    session: Session,
    target_date: date,
    icd_score: float | None = 72.5,
) -> DailyBiometrics:
    """Helper: inserta un DailyBiometrics mínimo para enlazar sesiones."""
    record = DailyBiometrics(date=target_date, icd_score=icd_score)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateStudySession:
    """Creación de sesiones con captura automática del ICD."""

    def test_create_session_with_icd_snapshot(self, db_session: Session) -> None:
        """icd_at_start se captura automáticamente desde DailyBiometrics."""
        today = date.today()
        _seed_biometrics(db_session, today, icd_score=72.5)

        session_data = {
            "date": today,
            "start_time": datetime.now().replace(second=0, microsecond=0),
            "duration_min": 45,
            "task_type": "coding",
            "focus_score": 7,
        }

        result = create_study_session(db_session, session_data)

        assert result.session_id is not None
        assert result.icd_at_start == pytest.approx(72.5)
        assert result.date == today
        assert result.task_type == "coding"

    def test_create_session_without_biometrics(self, db_session: Session) -> None:
        """Sin DailyBiometrics del día, icd_at_start queda None."""
        today = date.today()
        # No insertamos biometrics a propósito

        session_data = {
            "date": today,
            "start_time": datetime.now().replace(second=0, microsecond=0),
            "duration_min": 30,
        }

        result = create_study_session(db_session, session_data)

        assert result.session_id is not None
        assert result.icd_at_start is None

    def test_create_session_biometrics_without_icd(self, db_session: Session) -> None:
        """Si DailyBiometrics existe pero icd_score es None, icd_at_start queda None."""
        today = date.today()
        _seed_biometrics(db_session, today, icd_score=None)

        session_data = {
            "date": today,
            "start_time": datetime.now().replace(second=0, microsecond=0),
            "duration_min": 20,
        }

        result = create_study_session(db_session, session_data)

        assert result.icd_at_start is None

    def test_multiple_sessions_per_day(self, db_session: Session) -> None:
        """Se pueden crear varias sesiones el mismo día."""
        today = date.today()
        _seed_biometrics(db_session, today, icd_score=65.0)

        base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

        ids = []
        for i in range(3):
            data = {
                "date": today,
                "start_time": base_time.replace(hour=9 + i * 3),
                "duration_min": 50,
                "task_type": "math",
            }
            result = create_study_session(db_session, data)
            ids.append(result.session_id)

        # Tres sesiones distintas, misma fecha, ICD capturado en todas
        assert len(set(ids)) == 3
        for sid in ids:
            assert sid is not None

    def test_missing_date_raises(self, db_session: Session) -> None:
        """Omitir 'date' debe lanzar ValueError."""
        with pytest.raises(ValueError, match="date"):
            create_study_session(db_session, {"duration_min": 30})


class TestGetSessionsByDate:
    """Consulta de sesiones filtradas por fecha."""

    def test_get_sessions_by_date(self, db_session: Session) -> None:
        """Devuelve solo las sesiones del día solicitado."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        _seed_biometrics(db_session, today)
        _seed_biometrics(db_session, yesterday)

        base = datetime.now().replace(second=0, microsecond=0)

        # 2 sesiones hoy
        create_study_session(db_session, {
            "date": today,
            "start_time": base.replace(hour=10),
            "duration_min": 30,
        })
        create_study_session(db_session, {
            "date": today,
            "start_time": base.replace(hour=15),
            "duration_min": 45,
        })

        # 1 sesión ayer
        create_study_session(db_session, {
            "date": yesterday,
            "start_time": base.replace(hour=11),
            "duration_min": 60,
        })

        today_sessions = get_sessions_by_date(db_session, today)
        yesterday_sessions = get_sessions_by_date(db_session, yesterday)

        assert len(today_sessions) == 2
        assert len(yesterday_sessions) == 1

    def test_get_sessions_empty_date(self, db_session: Session) -> None:
        """Una fecha sin sesiones devuelve lista vacía."""
        result = get_sessions_by_date(db_session, date(2020, 1, 1))
        assert result == []

    def test_sessions_ordered_by_start_time(self, db_session: Session) -> None:
        """Las sesiones se devuelven ordenadas por hora de inicio ascendente."""
        today = date.today()
        _seed_biometrics(db_session, today)

        base = datetime.now().replace(second=0, microsecond=0)

        # Insertar en orden inverso
        create_study_session(db_session, {
            "date": today,
            "start_time": base.replace(hour=18),
            "duration_min": 20,
        })
        create_study_session(db_session, {
            "date": today,
            "start_time": base.replace(hour=9),
            "duration_min": 25,
        })

        sessions = get_sessions_by_date(db_session, today)

        assert sessions[0].start_time.hour == 9
        assert sessions[1].start_time.hour == 18


class TestGetRecentSessions:
    """Consulta de sesiones en ventana temporal."""

    def test_get_recent_sessions(self, db_session: Session) -> None:
        """Devuelve sesiones dentro de la ventana de N días."""
        today = date.today()
        three_days_ago = today - timedelta(days=3)
        ten_days_ago = today - timedelta(days=10)

        _seed_biometrics(db_session, today)
        _seed_biometrics(db_session, three_days_ago)
        _seed_biometrics(db_session, ten_days_ago)

        base = datetime.now().replace(second=0, microsecond=0)

        # Sesión hoy
        create_study_session(db_session, {
            "date": today,
            "start_time": base,
            "duration_min": 30,
        })
        # Sesión hace 3 días (dentro de ventana de 7)
        create_study_session(db_session, {
            "date": three_days_ago,
            "start_time": base,
            "duration_min": 40,
        })
        # Sesión hace 10 días (fuera de ventana de 7)
        create_study_session(db_session, {
            "date": ten_days_ago,
            "start_time": base,
            "duration_min": 50,
        })

        recent = get_recent_sessions(db_session, days=7)

        assert len(recent) == 2
        # Ordenadas por fecha descendente
        assert recent[0].date >= recent[1].date

    def test_get_recent_sessions_empty(self, db_session: Session) -> None:
        """Sin sesiones registradas, devuelve lista vacía."""
        recent = get_recent_sessions(db_session, days=7)
        assert recent == []
