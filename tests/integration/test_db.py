import time
from unittest.mock import MagicMock

from sqlalchemy import select

from src.db.models import Message, TickLog
from src.db.repository import get_recent_messages, log_tick, save_message


class TestSaveMessage:
    def test_save_message_success(self, in_memory_db):
        """Verifies messages are persisted with auto-incrementing ID and timestamp."""
        msg1 = save_message(db=in_memory_db, role="user", content="Hello Shorekeeper")
        msg2 = save_message(
            db=in_memory_db, role="assistant", content="The tides are peaceful."
        )

        assert msg1 is not None
        assert msg2 is not None
        assert msg1.id is not None
        assert msg2.id is not None
        assert msg2.id > msg1.id
        assert msg1.role == "user"
        assert msg1.content == "Hello Shorekeeper"
        assert msg2.role == "assistant"
        assert msg2.content == "The tides are peaceful."
        assert isinstance(msg1.ts, float)

    def test_save_message_rollback_on_failure(self, in_memory_db, monkeypatch):
        """Ensures that database errors trigger a rollback and return None."""
        monkeypatch.setattr(
            in_memory_db, "commit", MagicMock(side_effect=Exception("Database lock"))
        )

        result = save_message(db=in_memory_db, role="user", content="Broken attempt")

        assert result is None
        # Verify rollback left the session functional and clean
        monkeypatch.undo()
        remaining = in_memory_db.scalars(select(Message)).all()
        assert len(remaining) == 0


class TestGetRecentMessages:
    def test_get_recent_messages_order(self, in_memory_db):
        """Verifies limit selects the newest N messages, returned oldest -> newest."""
        base_ts = time.time()
        for i in range(10):
            msg = Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                ts=base_ts + i * 10,
            )
            in_memory_db.add(msg)
        in_memory_db.commit()

        recent = get_recent_messages(db=in_memory_db, limit=5)

        assert len(recent) == 5
        # The latest 5 messages are 5, 6, 7, 8, 9
        expected_contents = [f"Message {i}" for i in range(5, 10)]
        assert [m.content for m in recent] == expected_contents
        # Chronological order verified
        assert recent[0].ts < recent[-1].ts

    def test_get_recent_messages_empty_table(self, in_memory_db):
        """Verifies an empty table returns an empty list without raising errors."""
        result = get_recent_messages(db=in_memory_db, limit=10)
        assert result == []

    def test_get_recent_messages_less_than_limit(self, in_memory_db):
        """Verifies querying limit larger than available count returns all messages chronologically."""
        save_message(db=in_memory_db, role="user", content="First")
        save_message(db=in_memory_db, role="assistant", content="Second")

        recent = get_recent_messages(db=in_memory_db, limit=10)
        assert len(recent) == 2
        assert [m.content for m in recent] == ["First", "Second"]


class TestLogTick:
    def test_log_tick_serialization(self, in_memory_db, sample_llm_config):
        """Verifies tick_log record is committed with full payload parameters."""
        user_msg = save_message(db=in_memory_db, role="user", content="Prompt input")

        tick = log_tick(
            db=in_memory_db,
            trigger="user_message",
            last_msg_id=user_msg.id,
            prompt="System + User Prompt",
            output="Assistant Response",
            thinking="Step-by-step reasoning",
            params=sample_llm_config,
        )

        assert tick is not None
        assert tick.id is not None
        assert tick.trigger == "user_message"
        assert tick.last_msg_id == user_msg.id
        assert tick.prompt == "System + User Prompt"
        assert tick.output == "Assistant Response"
        assert tick.thinking == "Step-by-step reasoning"
        assert tick.params == sample_llm_config.to_payload_params()

        # Query back from DB to confirm persistence
        fetched = in_memory_db.scalars(
            select(TickLog).where(TickLog.id == tick.id)
        ).first()
        assert fetched is not None
        assert fetched.params["model"] == sample_llm_config.model

    def test_log_tick_without_params(self, in_memory_db):
        """Verifies log_tick handles None for params and thinking gracefully."""
        tick = log_tick(
            db=in_memory_db,
            trigger="timer",
            last_msg_id=0,
            prompt="Heartbeat",
            output="Ack",
            thinking=None,
            params=None,
        )

        assert tick is not None
        assert tick.params == {}
        assert tick.thinking is None

    def test_log_tick_rollback_on_failure(self, in_memory_db, monkeypatch):
        """Verifies failure on commit triggers rollback and returns None."""
        monkeypatch.setattr(
            in_memory_db, "commit", MagicMock(side_effect=Exception("Disk full"))
        )

        result = log_tick(
            db=in_memory_db,
            trigger="user_message",
            last_msg_id=1,
            prompt="Test",
            output="Test",
        )

        assert result is None
