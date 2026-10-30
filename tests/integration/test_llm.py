import pytest
import requests

from src.llm.client import llm_call
from src.llm.config import LLMConfig


class TestLLMCall:
    def test_llm_call_success(self, monkeypatch):
        """Verifies standard completion returns content and None for reasoning."""
        captured_kwargs = {}

        class MockResponse:
            status_code = 200
            text = "OK"

            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "choices": [
                        {"message": {"content": "Echoes across the sea."}}
                    ]
                }

        def mock_post(url, **kwargs):
            captured_kwargs["url"] = url
            captured_kwargs.update(kwargs)
            return MockResponse()

        monkeypatch.setattr("requests.post", mock_post)

        messages = [{"role": "user", "content": "Listen to the tides"}]
        config = LLMConfig(model="test-gemma", timeout=60.0)

        result = llm_call(messages=messages, config=config)

        assert result == ("Echoes across the sea.", None)
        assert captured_kwargs["json"]["messages"] == messages
        assert captured_kwargs["json"]["model"] == "test-gemma"
        assert captured_kwargs["timeout"] == 60.0
        assert captured_kwargs["headers"] == {"Content-Type": "application/json"}

    def test_llm_call_with_reasoning(self, monkeypatch):
        """Verifies models outputting reasoning_content return both content and thoughts."""

        class MockResponse:
            status_code = 200
            text = "OK"

            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "I am here with you.",
                                "reasoning_content": "Analyze user sentiment: affectionate.",
                            }
                        }
                    ]
                }

        monkeypatch.setattr("requests.post", lambda *args, **kwargs: MockResponse())

        messages = [{"role": "user", "content": "Are you there?"}]
        config = LLMConfig()

        result = llm_call(messages=messages, config=config)

        assert result == ("I am here with you.", "Analyze user sentiment: affectionate.")

    @pytest.mark.parametrize("status_code", [429, 500, 503])
    def test_llm_call_http_error(self, monkeypatch, status_code):
        """Verifies HTTP status errors (e.g. Rate Limit 429, Server 500) return None gracefully."""

        class MockErrorResponse:
            def __init__(self):
                self.status_code = status_code
                self.text = f"HTTP Error {status_code}"

            def raise_for_status(self):
                raise requests.HTTPError(
                    f"{self.status_code} Error", response=self
                )

        mock_resp = MockErrorResponse()
        monkeypatch.setattr("requests.post", lambda *args, **kwargs: mock_resp)

        result = llm_call(
            messages=[{"role": "user", "content": "Ping"}],
            config=LLMConfig(),
        )

        assert result is None

    def test_llm_call_timeout(self, monkeypatch):
        """Verifies network timeouts are caught and return None."""

        def mock_post(*args, **kwargs):
            raise requests.Timeout("Connection timed out after 90 seconds")

        monkeypatch.setattr("requests.post", mock_post)

        result = llm_call(
            messages=[{"role": "user", "content": "Timeout test"}],
            config=LLMConfig(),
        )

        assert result is None

    def test_llm_call_connection_error(self, monkeypatch):
        """Verifies connection failures return None without raising uncaught exceptions."""

        def mock_post(*args, **kwargs):
            raise requests.ConnectionError("Failed to connect to LLM server")

        monkeypatch.setattr("requests.post", mock_post)

        result = llm_call(
            messages=[{"role": "user", "content": "Connection error test"}],
            config=LLMConfig(),
        )

        assert result is None

    def test_llm_call_empty_choices(self, monkeypatch):
        """Verifies empty choices list returns None gracefully."""

        class MockEmptyChoices:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"choices": []}

        monkeypatch.setattr("requests.post", lambda *args, **kwargs: MockEmptyChoices())

        result = llm_call(
            messages=[{"role": "user", "content": "Empty choices test"}],
            config=LLMConfig(),
        )

        assert result is None

    def test_llm_call_malformed_json(self, monkeypatch):
        """Verifies non-JSON response payload on 200 OK returns None gracefully."""

        class MockMalformedResponse:
            status_code = 200
            text = "<html>502 Bad Gateway</html>"

            def raise_for_status(self):
                pass

            def json(self):
                raise ValueError("No JSON object could be decoded")

        monkeypatch.setattr(
            "requests.post", lambda *args, **kwargs: MockMalformedResponse()
        )

        result = llm_call(
            messages=[{"role": "user", "content": "Malformed JSON test"}],
            config=LLMConfig(),
        )

        assert result is None
