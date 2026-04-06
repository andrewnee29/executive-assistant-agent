from datetime import datetime
from typing import Any
from sqlalchemy import (
    Column, String, Text, DateTime, Integer, JSON, ForeignKey, Boolean
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String, primary_key=True)
    conference_id = Column(String, unique=True, nullable=False)
    title = Column(String)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    participants = Column(JSON, default=list)  # list of {name, email}
    recap = Column(Text)
    recap_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    transcript = relationship("Transcript", back_populates="meeting", uselist=False)
    action_items = relationship("ActionItem", back_populates="meeting")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String, primary_key=True)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False)
    entries = Column(JSON, default=list)  # list of {timestamp, speaker, text}
    raw_source = Column(String)  # "google_meet" | "manual_upload"
    created_at = Column(DateTime, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="transcript")


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(String, primary_key=True)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False)
    task = Column(Text, nullable=False)
    timestamp = Column(String)   # transcript timestamp citation
    context = Column(Text)       # surrounding quote
    status = Column(String, default="open")  # "open" | "done"
    google_task_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="action_items")


class Person(Base):
    __tablename__ = "people"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)
    role = Column(String)
    transcription_aliases = Column(JSON, default=list)  # known mis-transcriptions
    notes = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Term(Base):
    __tablename__ = "terms"

    id = Column(String, primary_key=True)
    term = Column(String, nullable=False)
    definition = Column(Text)
    category = Column(String)  # "project" | "acronym" | "tool" | "other"
    updated_at = Column(DateTime, default=datetime.utcnow)
