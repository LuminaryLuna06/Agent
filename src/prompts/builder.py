import datetime

from src.prompts.templates import SHOREKEEPER_PERSONA, VOICE_EXAMPLES
from src.tokens.counter import count_message_tokens


def build_message(history: list[dict], user_msg: str) -> list[dict]:
    """Appends current user turn accompanied by a timestamp context tail."""
    tail = f"[Context: Current time: {datetime.datetime.now():%H:%M}]"
    current_turn = {"role": "user", "content": f"{tail}. {user_msg}"}
    return [*history, current_turn]


def build_system_prompt(budget: int) -> list[dict] | None:
    """Constructs the system prompt ensuring it fits within the specified token budget."""
    persona = SHOREKEEPER_PERSONA
    anchor = VOICE_EXAMPLES
    turn = {"role": "system", "content": f"{persona.strip()}\n{anchor.strip()}"}
    if count_message_tokens(message=turn) < budget:
        return [turn]
    return None
