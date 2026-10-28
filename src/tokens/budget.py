from src.tokens.counter import count_message_tokens


def fit_newest_first(messages: list[dict], budget: int) -> list[dict]:
    """
    Selects the newest messages that fit strictly within the allotted token budget.
    Preserves chronological order (oldest to newest) in the returned list.
    """
    accumulated_tokens = 0
    selected_messages: list[dict] = []

    # Iterate from newest to oldest
    for msg in reversed(messages):
        cost = count_message_tokens(msg)
        if accumulated_tokens + cost <= budget:
            accumulated_tokens += cost
            selected_messages.append(msg)
        else:
            # Memory shore reached; oldest ripples drift away
            break

    # Restore chronological order
    selected_messages.reverse()
    return selected_messages


def dynamic_budget(
    budget: int, persona: int = 600, anchor: int = 200, reply: int = 2000
) -> dict[str, int] | None:
    """Dynamically calculates token allocations for persona, chat, anchor, and reply."""
    budget_left = budget - persona - anchor - reply
    if budget_left > 0:
        return {
            "persona": persona,
            "chat": budget_left,
            "anchor": anchor,
            "reply": reply,
        }
    return None
