import pytest
from sqlalchemy import select

from src.agent.agent import ShorekeeperAgent
from src.db.models import Message, TickLog
from src.db.repository import save_message
from src.llm.config import LLMConfig


class TestShorekeeperAgentInitialization:
    def test_agent_init_success(self, in_memory_db, sample_llm_config):
        """Verifies agent initializes with empty history when database has no prior messages."""
        agent = ShorekeeperAgent(db=in_memory_db, config=sample_llm_config)

        assert agent.budget is not None
        assert agent.budget["chat"] > 0
        assert agent.system_prompt is not None
        assert len(agent.system_prompt) == 1
        assert agent.system_prompt[0]["role"] == "system"
        assert agent.messages == []

    def test_agent_init_with_prior_db_history(self, in_memory_db, sample_llm_config):
        """Verifies agent preloads existing messages from database upon initialization."""
        save_message(db=in_memory_db, role="user", content="Past question")
        save_message(db=in_memory_db, role="assistant", content="Past answer")

        agent = ShorekeeperAgent(db=in_memory_db, config=sample_llm_config)

        assert len(agent.messages) == 2
        assert agent.messages[0] == {"role": "user", "content": "Past question"}
        assert agent.messages[1] == {"role": "assistant", "content": "Past answer"}

    def test_agent_init_insufficient_context_window(self, in_memory_db):
        """Verifies agent raises ValueError if context window cannot accommodate fixed overheads."""
        with pytest.raises(ValueError, match="Not enough Budget to start"):
            ShorekeeperAgent(db=in_memory_db, context_window=100)

    def test_agent_init_insufficient_system_prompt_budget(
        self, in_memory_db, monkeypatch
    ):
        """Verifies agent raises ValueError if system prompt tokens exceed the allocated budget."""
        # Force dynamic_budget to allocate practically zero budget for persona and anchor
        fake_budget = {"persona": 1, "anchor": 1, "reply": 100, "chat": 100}
        monkeypatch.setattr("src.agent.agent.dynamic_budget", lambda **kwargs: fake_budget)

        with pytest.raises(ValueError, match="System prompt budget not enough"):
            ShorekeeperAgent(db=in_memory_db)


class TestShorekeeperAgentTurnExecution:
    def test_agent_step_successful_turn(
        self, in_memory_db, sample_llm_config, mock_llm_response
    ):
        """Verifies end-to-end single conversational turn persistence and log generation."""
        mock_llm_response(
            content="The tides are calm today, Rover.",
            reasoning="Rover has returned to the shore.",
        )

        agent = ShorekeeperAgent(db=in_memory_db, config=sample_llm_config)
        prompt_text = "Guide me through the stars."

        response = agent.step(user_msg=prompt_text)

        assert response == "The tides are calm today, Rover."

        # Verify DB messages: 1 user, 1 assistant
        db_messages = in_memory_db.scalars(
            select(Message).order_by(Message.id.asc())
        ).all()
        assert len(db_messages) == 2
        assert db_messages[0].role == "user"
        assert db_messages[0].content == prompt_text
        assert db_messages[1].role == "assistant"
        assert db_messages[1].content == "The tides are calm today, Rover."

        # Verify tick log entry
        db_ticks = in_memory_db.scalars(select(TickLog)).all()
        assert len(db_ticks) == 1
        tick = db_ticks[0]
        assert tick.trigger == "user_message"
        assert tick.last_msg_id == db_messages[0].id
        assert tick.output == "The tides are calm today, Rover."
        assert tick.thinking == "Rover has returned to the shore."
        assert tick.params["model"] == sample_llm_config.model
        assert prompt_text in tick.prompt

        # Verify agent's internal message state
        assert agent.messages[-1] == {
            "role": "assistant",
            "content": "The tides are calm today, Rover.",
        }

    def test_agent_step_multi_turn_history_accumulation(
        self, in_memory_db, sample_llm_config, monkeypatch
    ):
        """Verifies that consecutive steps accumulate dialogue history cleanly."""
        turn_responses = [
            ("First answer.", None),
            ("Second answer.", "Reasoning step 2"),
        ]

        def mock_llm_call(messages, config):
            return turn_responses.pop(0)

        monkeypatch.setattr("src.agent.agent.llm_call", mock_llm_call)

        agent = ShorekeeperAgent(db=in_memory_db, config=sample_llm_config)

        res1 = agent.step("Query 1")
        assert res1 == "First answer."

        res2 = agent.step("Query 2")
        assert res2 == "Second answer."

        # Total 4 messages in database
        db_messages = in_memory_db.scalars(
            select(Message).order_by(Message.id.asc())
        ).all()
        assert len(db_messages) == 4
        assert [m.role for m in db_messages] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]

        # Total 2 tick logs in database
        db_ticks = in_memory_db.scalars(
            select(TickLog).order_by(TickLog.id.asc())
        ).all()
        assert len(db_ticks) == 2
        assert db_ticks[0].output == "First answer."
        assert db_ticks[1].output == "Second answer."
        assert db_ticks[1].thinking == "Reasoning step 2"

    def test_agent_step_llm_failure_does_not_persist_assistant_message(
        self, in_memory_db, sample_llm_config, monkeypatch
    ):
        """Verifies that if the LLM fails, assistant message and tick log are not committed."""
        monkeypatch.setattr("src.agent.agent.llm_call", lambda messages, config: (None, None))

        agent = ShorekeeperAgent(db=in_memory_db, config=sample_llm_config)
        result = agent.step("Can you hear me?")

        assert result is None

        # User message was saved prior to LLM call
        db_messages = in_memory_db.scalars(select(Message)).all()
        assert len(db_messages) == 1
        assert db_messages[0].role == "user"
        assert db_messages[0].content == "Can you hear me?"

        # Tick log was not created
        db_ticks = in_memory_db.scalars(select(TickLog)).all()
        assert len(db_ticks) == 0

        # Agent messages should not contain an assistant response
        assert not any(m["role"] == "assistant" for m in agent.messages)
