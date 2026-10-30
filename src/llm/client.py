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

        data = response.json()
        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            print("Invalid response format: 'choices' field is missing or not a list.")
            return None

        message = choices[0].get("message")
        if not message or "content" not in message:
            print("Invalid response format: 'message' field is missing or incomplete.")
            return None

        if "reasoning_content" in message:
            return message["content"], message["reasoning_content"]

        return message["content"], None

    except requests.HTTPError:
        print(f"HTTP error occurred: {response.status_code} - {response.text}")
        return None
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except (ValueError, KeyError, IndexError) as e:
        print(f"Failed to parse LLM response payload: {e}")
        return None
