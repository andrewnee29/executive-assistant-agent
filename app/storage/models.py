from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String, primary_key=True)  # conference_id
    title = Column(String)
    date = Column(DateTime)
    participants = Column(JSON, default=list)
    duration_seconds = Column(Integer)
    processed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    recap = relationship("Recap", back_populates="meeting", uselist=False)
    action_items = relationship("ActionItem", back_populates="meeting")


class Recap(Base):
    __tablename__ = "recaps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False)
    summary = Column(Text, nullable=False)
    uncertainties = Column(JSON, default=list)
    approved_at = Column(DateTime, nullable=False)

    meeting = relationship("Meeting", back_populates="recap")


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False)
    task = Column(Text, nullable=False)
    timestamp = Column(String)
    context = Column(Text)
    done = Column(Boolean, default=False, nullable=False)
    tasks_id = Column(String)  # Google Tasks ID, set after push

    meeting = relationship("Meeting", back_populates="action_items")


class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    role = Column(String)
    email = Column(String)
    aliases = Column(JSON, default=list)


class Term(Base):
    __tablename__ = "terms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    term = Column(String, nullable=False)
    definition = Column(String)
    category = Column(String)


class UserCredentials(Base):
    __tablename__ = "user_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Single-user MVP: one row, always user_id = "default"
    user_id = Column(String, unique=True, nullable=False, default="default")
    credentials_json = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
