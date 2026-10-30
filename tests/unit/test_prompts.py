import datetime
import re
from unittest.mock import patch

from src.prompts.builder import build_message, build_system_prompt
from src.prompts.templates import SHOREKEEPER_PERSONA, VOICE_EXAMPLES
from src.tokens.counter import count_message_tokens


class TestBuildSystemPrompt:
    def test_build_system_prompt_within_budget(self):
        """Verifies system prompt is returned when token cost is strictly within budget."""
        system_turn = {
            "role": "system",
            "content": f"{SHOREKEEPER_PERSONA.strip()}\n{VOICE_EXAMPLES.strip()}",
        }
        cost = count_message_tokens(system_turn)

        result = build_system_prompt(budget=cost + 10)

        assert result is not None
        assert len(result) == 1
        assert result[0]["role"] == "system"
        assert SHOREKEEPER_PERSONA.strip() in result[0]["content"]
        assert VOICE_EXAMPLES.strip() in result[0]["content"]

    def test_build_system_prompt_overflow(self):
        """Verifies None is returned when budget cannot accommodate system prompt tokens."""
        # A tiny budget of 10 tokens will definitely trigger an overflow
        result = build_system_prompt(budget=10)
        assert result is None

    def test_build_system_prompt_exact_boundary(self):
        """Verifies boundary condition: if cost == budget, it returns None (< condition)."""
        system_turn = {
            "role": "system",
            "content": f"{SHOREKEEPER_PERSONA.strip()}\n{VOICE_EXAMPLES.strip()}",
        }
        cost = count_message_tokens(system_turn)

        result = build_system_prompt(budget=cost)
        assert result is None


class TestBuildMessage:
    def test_build_message_formatting(self):
        """Verifies current turn has timestamp prefix and user message body."""
        history = [{"role": "assistant", "content": "Welcome back, Rover."}]
        user_msg = "Where are the stars leading us?"

        result = build_message(history=history, user_msg=user_msg)

        assert len(result) == 2
        assert result[0] == history[0]

        new_turn = result[1]
        assert new_turn["role"] == "user"
        pattern = (
            r"^\[Context: Current time: \d{2}:\d{2}\]\. " + re.escape(user_msg) + r"$"
        )
        assert re.match(pattern, new_turn["content"])

    def test_build_message_with_empty_history(self):
        """Verifies message construction with an empty history."""
        user_msg = "Hello Shorekeeper"
        result = build_message(history=[], user_msg=user_msg)

        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert user_msg in result[0]["content"]

    def test_build_message_mocked_time(self):
        """Verifies exact timestamp formatting with mocked datetime."""
        fixed_dt = datetime.datetime(2026, 10, 28, 14, 30)

        class MockDateTime(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_dt

        with patch("datetime.datetime", MockDateTime):
            result = build_message(history=[], user_msg="Synchronize frequencies")

        assert (
            result[0]["content"]
            == "[Context: Current time: 14:30]. Synchronize frequencies"
        )
