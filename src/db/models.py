import time

from sqlalchemy import DATETIME, Column, Float, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[float] = mapped_column(Float, default=time.time, index=True)
    role: Mapped[str] = mapped_column(String(16))  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text)


class StateField(Base):
    __tablename__ = "state"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at = Column(DATETIME)


class TickLog(Base):
    __tablename__ = "tick_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[float] = mapped_column(Float, default=time.time, index=True)
    trigger: Mapped[str] = mapped_column(
        String(32)
    )  # 'user_message' now, 'timer' later
    last_msg_id: Mapped[int] = mapped_column(Integer)
    prompt: Mapped[str] = mapped_column(Text)
    thinking: Mapped[str] = mapped_column(Text, nullable=True)
    output: Mapped[str] = mapped_column(Text)
    params: Mapped[dict] = mapped_column(JSON)
