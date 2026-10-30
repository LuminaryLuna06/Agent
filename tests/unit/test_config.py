import pytest
from pydantic import ValidationError

from src.llm.config import LLMConfig


class TestLLMConfig:
    def test_llm_config_defaults(self):
        """Verifies default hyperparameters match expected baseline settings."""
        config = LLMConfig()

        assert config.model == "default"
        assert config.timeout == 90.0
        assert config.max_retries == 2
        assert config.reasoning_effort is None
        assert config.enable_thinking is None
        assert config.temperature == 0.8
        assert config.top_p == 0.9
        assert config.min_p == 0.05
        assert config.repeat_penalty == 1.1
        assert config.frequency_penalty == 0.2
        assert config.presence_penalty == 0.1

    def test_to_payload_params_structure(self):
        """Verifies nested payload format matches the OpenAI/vLLM completion schema."""
        config = LLMConfig(
            model="Gemma4-12B",
            enable_thinking=True,
            reasoning_effort="medium",
            temperature=0.7,
            top_p=0.95,
        )

        payload = config.to_payload_params()

        assert payload["model"] == "Gemma4-12B"
        assert payload["chat_template_kwargs"] == {"enable_thinking": True}
        assert payload["reasoning_effort"] == "medium"
        assert payload["temperature"] == 0.7
        assert payload["top_p"] == 0.95
        assert payload["min_p"] == 0.05
        assert payload["repeat_penalty"] == 1.1
        assert payload["frequency_penalty"] == 0.2
        assert payload["presence_penalty"] == 0.1
        # timeout and max_retries should not be included in the inference payload dictionary
        assert "timeout" not in payload
        assert "max_retries" not in payload

    def test_pydantic_type_validation_rejects_invalid_types(self):
        """Ensures Pydantic raises ValidationError when given incompatible parameter types."""
        with pytest.raises(ValidationError):
            LLMConfig(temperature="not-a-number")

        with pytest.raises(ValidationError):
            LLMConfig(max_retries="three")

        with pytest.raises(ValidationError):
            LLMConfig(enable_thinking="not-a-bool")

    def test_custom_values_assignment(self):
        """Verifies custom values are correctly stored on the model instance."""
        config = LLMConfig(
            model="custom-shorekeeper",
            timeout=45.0,
            max_retries=5,
            reasoning_effort="high",
            enable_thinking=False,
            temperature=0.5,
        )

        assert config.model == "custom-shorekeeper"
        assert config.timeout == 45.0
        assert config.max_retries == 5
        assert config.reasoning_effort == "high"
        assert config.enable_thinking is False
        assert config.temperature == 0.5
