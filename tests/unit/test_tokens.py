from src.tokens.budget import dynamic_budget, fit_newest_first
from src.tokens.counter import count_message_tokens, count_tokens


class TestCountTokens:
    def test_count_tokens_empty(self):
        """Verifies that None or empty strings yield 0 tokens."""
        assert count_tokens("") == 0
        assert count_tokens(None) == 0

    def test_count_tokens_tiktoken(self):
        """Verifies accurate token calculation via tiktoken."""
        # 'Hello, world!' in cl100k_base encodes to 4 tokens
        text = "Hello, world!"
        assert count_tokens(text) == 4

    def test_count_tokens_fallback(self, monkeypatch):
        """Verifies the heuristic fallback (~3.8 chars/token) when tiktoken is unavailable."""
        import src.tokens.counter as counter_mod

        monkeypatch.setattr(counter_mod, "_ENCODER", None)
        text = "This is a simple text sentence for testing fallback."
        expected = max(1, int(len(text) / 3.8))
        assert count_tokens(text) == expected


class TestCountMessageTokens:
    def test_count_message_tokens_framing(self):
        """Verifies framing overhead (4 tokens) is added to role and content tokens."""
        message = {"role": "user", "content": "Hello"}
        expected = 4 + count_tokens("user") + count_tokens("Hello")
        assert count_message_tokens(message) == expected


class TestDynamicBudget:
    def test_dynamic_budget_valid(self):
        """Verifies context window splits cleanly into allocated segments."""
        budget = dynamic_budget(budget=8000, persona=600, anchor=200, reply=2000)
        assert budget is not None
        assert budget["persona"] == 600
        assert budget["anchor"] == 200
        assert budget["reply"] == 2000
        assert budget["chat"] == 8000 - 600 - 200 - 2000  # 5200

    def test_dynamic_budget_exhausted(self):
        """Returns None when budget cannot fulfill fixed overheads."""
        # Total fixed overhead: 600 + 200 + 2000 = 2800
        assert dynamic_budget(budget=2800, persona=600, anchor=200, reply=2000) is None
        assert dynamic_budget(budget=1000, persona=600, anchor=200, reply=2000) is None


class TestFitNewestFirst:
    def test_fit_all_messages(self):
        """Verifies all messages are retained if they fit within budget."""
        messages = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Greetings"},
        ]
        total_tokens = sum(count_message_tokens(m) for m in messages)
        result = fit_newest_first(messages, budget=total_tokens + 10)
        assert result == messages

    def test_fit_prunes_oldest_first(self):
        """Verifies that older messages are discarded while newer ones are preserved."""
        msg1 = {"role": "user", "content": "First message from long ago"}
        msg2 = {"role": "assistant", "content": "Second response"}
        msg3 = {"role": "user", "content": "Third newest query"}

        messages = [msg1, msg2, msg3]
        cost3 = count_message_tokens(msg3)
        cost2 = count_message_tokens(msg2)

        # Budget allows msg2 and msg3, but not msg1
        budget = cost2 + cost3
        result = fit_newest_first(messages, budget=budget)

        assert len(result) == 2
        assert result == [msg2, msg3]

    def test_fit_preserves_chronological_order(self):
        """Verifies the final list is strictly ordered oldest -> newest."""
        messages = [
            {"role": "user", "content": "Turn 1"},
            {"role": "assistant", "content": "Turn 2"},
            {"role": "user", "content": "Turn 3"},
        ]
        result = fit_newest_first(messages, budget=500)
        assert [m["content"] for m in result] == ["Turn 1", "Turn 2", "Turn 3"]

    def test_fit_single_message_exceeds_budget(self):
        """Returns an empty list if even the single newest message exceeds budget."""
        messages = [{"role": "user", "content": "A long message exceeding budget"}]
        cost = count_message_tokens(messages[0])
        result = fit_newest_first(messages, budget=cost - 1)
        assert result == []
