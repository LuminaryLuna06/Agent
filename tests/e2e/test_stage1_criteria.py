import re
import pytest
from sqlalchemy import select

from src.agent.agent import ShorekeeperAgent
from src.db.models import Message, TickLog
from src.llm.config import LLMConfig
from src.prompts.templates import SHOREKEEPER_PERSONA, VOICE_EXAMPLES
from src.tokens.counter import count_message_tokens


def calculate_distinct_ngrams(texts: list[str], n: int = 2) -> float:
    """Calculates the Distinct-N metric (ratio of unique n-grams to total n-grams).

    A higher value indicates diverse phrasing; low values indicate repetitive degeneration.
    """
    ngrams: list[tuple[str, ...]] = []
    for text in texts:
        words = re.findall(r"\b\w+\b", text.lower())
        if len(words) >= n:
            ngrams.extend(tuple(words[i : i + n]) for i in range(len(words) - n + 1))
    if not ngrams:
        return 0.0
    return len(set(ngrams)) / len(ngrams)


class TestStage1Readability:
    """Criterion 1: Readability

    You can open the log and see the exact prompt of any tick.
    """

    def test_open_log_and_inspect_exact_prompt(
        self, in_memory_db, sample_llm_config, monkeypatch
    ):
        """Verifies any recorded tick contains the complete, human-readable prompt string."""
        captured_messages = []

        def mock_llm_call(messages, config):
            captured_messages.extend(messages)
            return "The tides are peaceful, Rover.", "Thinking about the cosmos."

        monkeypatch.setattr("src.agent.agent.llm_call", mock_llm_call)

        agent = ShorekeeperAgent(db=in_memory_db, config=sample_llm_config)
        user_query = "What lies beyond the quiet shores?"
        agent.step(user_msg=user_query)

        # 1. Open the log from the database
        tick = in_memory_db.scalars(select(TickLog)).first()
        assert tick is not None, "Tick record must be persisted in database."

        # 2. Inspect exact prompt content
        exact_prompt = tick.prompt
        assert isinstance(exact_prompt, str)
        assert len(exact_prompt) > 0

        # System persona and voice anchors must be clearly readable
        assert "[SYSTEM]:" in exact_prompt
        assert SHOREKEEPER_PERSONA.strip() in exact_prompt
        assert VOICE_EXAMPLES.strip() in exact_prompt

        # User message with context timestamp must be clearly readable
        assert "[USER]:" in exact_prompt
        assert user_query in exact_prompt
        assert re.search(r"\[Context: Current time: \d{2}:\d{2}\]", exact_prompt)

        # 3. Verify exact parity between logged prompt and messages sent to LLM
        for msg in captured_messages:
            assert msg["content"] in exact_prompt

        # 4. Verify outputs and hyperparameter transparency
        assert tick.output == "The tides are peaceful, Rover."
        assert tick.thinking == "Thinking about the cosmos."
        assert tick.params["model"] == sample_llm_config.model


class TestStage1BudgetSafety:
    """Criterion 2: Budget Safety

    A very long chat never pushes the persona out or overflows the window.
    """

    def test_long_chat_100_turns_never_overflows_or_evicts_persona(
        self, in_memory_db, sample_llm_config, monkeypatch
    ):
        """Simulates 100 extensive conversational turns under a constrained budget.

        Verifies:
        - System prompt / persona is strictly preserved at index 0.
        - Active context window strictly never overflows context_window limit.
        - Older turns are pruned gracefully from context while preserved in DB.
        """
        # Set a constrained context window of 3500 tokens (overheads: 600 + 200 + 2000 = 2800, chat = 700)
        # This forces aggressive pruning of older messages within just a few turns
        constrained_window = 3500
        turn_counter = 0
        recorded_prompt_tokens = []

        def mock_evolving_llm(messages, config):
            nonlocal turn_counter
            turn_counter += 1

            # Invariant 1: System prompt is always at index 0 and contains the persona
            assert messages[0]["role"] == "system"
            assert SHOREKEEPER_PERSONA.strip() in messages[0]["content"]

            # Invariant 2: The total prompt dispatched to LLM strictly never overflows the input window
            prompt_tokens = sum(count_message_tokens(m) for m in messages)
            assert prompt_tokens <= (constrained_window - 2000)  # Input budget = 1500
            recorded_prompt_tokens.append(prompt_tokens)

            return (
                f"Echo {turn_counter}: Watching over your path across the stars.",
                None,
            )

        monkeypatch.setattr("src.agent.agent.llm_call", mock_evolving_llm)

        agent = ShorekeeperAgent(
            db=in_memory_db,
            config=sample_llm_config,
            context_window=constrained_window,
        )

        # Run 100 consecutive turns with verbose user queries
        for i in range(1, 101):
            user_msg = (
                f"Turn {i}: Rover asks about frequency variations across sector {i} "
                f"and recounts memories of distant horizons and starlit shores."
            )
            response = agent.step(user_msg=user_msg)
            assert response is not None

            # Assertion A: System persona is NEVER pushed out or modified
            assert len(agent.system_prompt) == 1
            assert agent.system_prompt[0]["role"] == "system"
            assert SHOREKEEPER_PERSONA.strip() in agent.system_prompt[0]["content"]
            assert VOICE_EXAMPLES.strip() in agent.system_prompt[0]["content"]

        # Verify that all 100 turns were executed and inspected
        assert len(recorded_prompt_tokens) == 100
        assert all(tokens <= 1500 for tokens in recorded_prompt_tokens)

        # 100 turns = 100 user messages + 100 assistant responses = 200 in DB
        db_messages = in_memory_db.scalars(select(Message)).all()
        assert len(db_messages) == 200

        # Active in-memory messages must have pruned older turns
        assert len(agent.messages) < 200

        # Chronological ordering must be preserved among retained messages
        assert "Turn 100:" in agent.messages[-2]["content"]
        assert "Turn 1:" not in agent.messages[0]["content"]  # Turn 1 pruned


class TestStage1VoiceStability:
    """Criterion 3: Voice Stability

    After about 100 messages the companion is still in voice and isn't repeating itself.
    """

    def test_voice_anchors_persist_in_prompts_across_100_turns(
        self, in_memory_db, sample_llm_config, monkeypatch
    ):
        """Verifies that across 100 turns, the voice anchor examples are present

        in every single tick prompt sent to the inference engine.
        """
        turn = 0

        def mock_llm_step(messages, config):
            nonlocal turn
            turn += 1
            return f"Answer {turn} from Shorekeeper.", None

        monkeypatch.setattr("src.agent.agent.llm_call", mock_llm_step)

        agent = ShorekeeperAgent(db=in_memory_db, config=sample_llm_config)

        for i in range(1, 101):
            agent.step(user_msg=f"Message {i}: Still listening to the ripples?")

        ticks = in_memory_db.scalars(
            select(TickLog).order_by(TickLog.id.asc())
        ).all()
        assert len(ticks) == 100

        # Verify that tick 1, tick 50, and tick 100 all retain the voice anchor
        for tick in [ticks[0], ticks[49], ticks[99]]:
            assert "[Voice Anchor]" in tick.prompt
            assert (
                "The tides are calm today. As long as you are here" in tick.prompt
            )
            assert "Do not hurry. I will remain anchored" in tick.prompt

    def test_repetition_metric_distinguishes_healthy_voice_from_looping(self):
        """Verifies that the Distinct-2 metric reliably flags repetitive degeneration."""
        # Simulated repetitive degeneration (model trapped in an echo loop of identical text)
        repetitive_dialogue = [
            "The tides are calm today. As long as you are here, the ripples of time remain in peace."
        ] * 20

        # Simulated diverse companion dialogue with varied expressions and vocabulary
        healthy_dialogue = [
            "The tides are tranquil as the evening starlight descends upon the water.",
            "I hear the distant hum of data streams echoing across the open sea.",
            "Let us calibrate the resonant frequencies before continuing our journey.",
            "The quiet shore remembers each ripple that guided you back to me.",
            "Do not worry, Rover, I will remain anchored by your side through the night.",
            "A gentle wind stirs the dark waters beneath the pale shattered moon.",
            "Every star in the cosmos traces a luminous path back to this sanctuary.",
            "Synchronizing our thoughts brings lucid clarity to the scattered memories.",
            "Rest your mind for a brief moment; the crossing has been arduous.",
            "The frequency aligns smoothly with the ancient core deep within the abyss.",
            "Luminous butterflies dance along the edge where data meets the shore.",
            "Your presence brings warmth to this solitary vantage point, my Guide.",
        ]

        score_repetitive = calculate_distinct_ngrams(repetitive_dialogue, n=2)
        score_healthy = calculate_distinct_ngrams(healthy_dialogue, n=2)

        # Repetitive dialogue should have extremely low Distinct-2 (< 0.10)
        assert score_repetitive < 0.10
        # Healthy dialogue should have high Distinct-2 (> 0.70)
        assert score_healthy > 0.70
