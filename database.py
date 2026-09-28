"""
database.py — MindLog v2.0 SQLAlchemy models and DB helpers.
"""

from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float,
    Integer, String, Text, create_engine, func, desc,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import DB_URL


class Base(DeclarativeBase):
    pass


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    username     = Column(String(100), nullable=False, index=True)
    entry_date   = Column(DateTime,    nullable=False, index=True)

    mood_score   = Column(Integer, nullable=False)
    stress_score = Column(Integer, nullable=False)
    energy_level = Column(Integer, nullable=True)
    sleep_hours  = Column(Float,   nullable=True)

    journal_notes   = Column(Text,         nullable=True)
    gratitude_notes = Column(Text,         nullable=True)
    activities      = Column(String(1000), nullable=True)

    ai_insight     = Column(Text,    nullable=True)
    ai_flagged     = Column(Boolean, default=False)
    ai_flag_reason = Column(Text,    nullable=True)
    ai_suggestion  = Column(Text,    nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)


class TherapistNote(Base):
    __tablename__ = "therapist_notes"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    username     = Column(String(100), nullable=False, index=True)
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)
    period_start = Column(DateTime, nullable=False)
    period_end   = Column(DateTime, nullable=False)
    report_text  = Column(Text, nullable=False)
    concerning_patterns = Column(Text, nullable=True)
    recommendations     = Column(Text, nullable=True)


_engine      = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def init_db() -> None:
    Base.metadata.create_all(_engine)


def get_session() -> Session:
    return SessionLocal()


def upsert_entry(
    username: str, entry_date: datetime.date,
    mood_score: int, stress_score: int,
    energy_level: Optional[int], sleep_hours: Optional[float],
    journal_notes: str, gratitude_notes: str, activities: str,
) -> JournalEntry:
    session = get_session()
    try:
        dt = datetime.datetime.combine(entry_date, datetime.time.min)
        entry = (
            session.query(JournalEntry)
            .filter(JournalEntry.username == username,
                    func.date(JournalEntry.entry_date) == entry_date.isoformat())
            .first()
        )
        if entry is None:
            entry = JournalEntry(username=username, entry_date=dt)
            session.add(entry)
        entry.mood_score     = mood_score
        entry.stress_score   = stress_score
        entry.energy_level   = energy_level
        entry.sleep_hours    = sleep_hours
        entry.journal_notes  = journal_notes
        entry.gratitude_notes= gratitude_notes
        entry.activities     = activities
        entry.updated_at     = datetime.datetime.utcnow()
        session.commit()
        session.refresh(entry)
        return entry
    finally:
        session.close()


def get_entry_for_date(username: str, entry_date: datetime.date) -> Optional[JournalEntry]:
    session = get_session()
    try:
        return (
            session.query(JournalEntry)
            .filter(JournalEntry.username == username,
                    func.date(JournalEntry.entry_date) == entry_date.isoformat())
            .first()
        )
    finally:
        session.close()


def get_entries(username: str, days: int = 30) -> list[JournalEntry]:
    session = get_session()
    try:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        return (
            session.query(JournalEntry)
            .filter(JournalEntry.username == username,
                    JournalEntry.entry_date >= cutoff)
            .order_by(desc(JournalEntry.entry_date))
            .all()
        )
    finally:
        session.close()


def get_all_entries(username: str) -> list[JournalEntry]:
    session = get_session()
    try:
        return (
            session.query(JournalEntry)
            .filter(JournalEntry.username == username)
            .order_by(desc(JournalEntry.entry_date))
            .all()
        )
    finally:
        session.close()


def update_ai_fields(entry_id: int, ai_insight: str, ai_flagged: bool,
                     ai_flag_reason: str, ai_suggestion: str = "") -> None:
    session = get_session()
    try:
        entry = session.get(JournalEntry, entry_id)
        if entry:
            entry.ai_insight     = ai_insight
            entry.ai_flagged     = ai_flagged
            entry.ai_flag_reason = ai_flag_reason
            entry.ai_suggestion  = ai_suggestion
            session.commit()
    finally:
        session.close()


def save_therapist_note(
    username: str, period_start: datetime.datetime, period_end: datetime.datetime,
    report_text: str, concerning_patterns: str, recommendations: str,
) -> TherapistNote:
    session = get_session()
    try:
        note = TherapistNote(
            username=username, period_start=period_start, period_end=period_end,
            report_text=report_text, concerning_patterns=concerning_patterns,
            recommendations=recommendations,
        )
        session.add(note)
        session.commit()
        session.refresh(note)
        return note
    finally:
        session.close()


def get_latest_therapist_note(username: str) -> Optional[TherapistNote]:
    session = get_session()
    try:
        return (
            session.query(TherapistNote)
            .filter(TherapistNote.username == username)
            .order_by(desc(TherapistNote.generated_at))
            .first()
        )
    finally:
        session.close()


