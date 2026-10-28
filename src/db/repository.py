from sqlite3 import OperationalError

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from src.db.models import Message, TickLog
from src.llm.config import LLMConfig


def save_message(db: Session, role: str, content: str) -> Message | None:
    """Saves a message into the database."""
    try:
        db_message = Message(role=role, content=content)
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        return db_message
    except Exception as e:  # noqa: BLE001
        db.rollback()
        print("An error occured:", e)
        return None


def get_recent_messages(db: Session, limit: int) -> list[Message]:
    """Retrieves newest messages up to limit, re-sorted chronologically (oldest to newest)."""
    try:
        # 1. Inner query: Grab the newest messages first
        subq = select(Message).order_by(Message.ts.desc()).limit(limit).subquery()

        # 2. Outer query: Alias back to the model and re-sort from oldest to newest
        aliased_message = aliased(Message, subq)
        stmt = select(aliased_message).order_by(aliased_message.ts.asc())

        messages = db.scalars(stmt).all()
        if messages:
            return list(messages)
        return []
    except OperationalError as e:
        print("Error occured:", e)
        return []


def log_tick(
    db: Session,
    trigger: str,
    last_msg_id: int,
    prompt: str,
    output: str,
    thinking: str | None = None,
    params: LLMConfig | None = None,
) -> TickLog | None:
    """Logs a single turn/tick into the tick_log table."""
    try:
        db_tick = TickLog(
            trigger=trigger,
            last_msg_id=last_msg_id,
            prompt=prompt,
            output=output,
            thinking=thinking,
            params=params.to_payload_params() if params else {},
        )
        db.add(db_tick)
        db.commit()
        db.refresh(db_tick)
        return db_tick
    except Exception as e:  # noqa: BLE001
        db.rollback()
        print("Error occured:", e)
        return None
