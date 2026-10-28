from pydantic import BaseModel


class LLMConfig(BaseModel):
    model: str = "default"
    timeout: float = 90.0
    max_retries: int = 2
    reasoning_effort: str | None = (
        None  # default | minimal | low | medium | high | xhigh | max (Gemma4-12B doesn't receive this parameter, only enable_thinking)
    )
    enable_thinking: bool | None = None
    temperature: float = 0.8
    top_p: float = 0.9
    min_p: float = 0.05
    repeat_penalty: float = 1.1
    frequency_penalty: float = 0.2
    presence_penalty: float = 0.1

    def to_payload_params(self) -> dict:
        return {
            "model": self.model,
            "chat_template_kwargs": {"enable_thinking": self.enable_thinking},
            "reasoning_effort": self.reasoning_effort,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "min_p": self.min_p,
            "repeat_penalty": self.repeat_penalty,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
        }
