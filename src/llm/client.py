import requests

from src.config.settings import LLAMA_URL
from src.llm.config import LLMConfig


def llm_call(messages: list[dict], config: LLMConfig) -> tuple[str, str | None] | None:
    """Dispatches a chat completion request to the OpenAI-compatible LLM endpoint."""
    try:
        url = f"{LLAMA_URL}/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload = {
            "messages": messages,
            **config.to_payload_params(),
        }
        response = requests.post(
            url, json=payload, headers=headers, timeout=config.timeout
        )
        response.raise_for_status()
    except requests.HTTPError:
        print(f"HTTP error occurred: {response.status_code} - {response.text}")
        return None
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None

    response_data = response.json()["choices"][0]["message"]
    if "reasoning_content" in response_data:
        return response_data["content"], response_data["reasoning_content"]

    return response_data["content"], None
