try:
    import tiktoken
    _ENCODER = tiktoken.get_encoding("cl100k_base")
except ImportError:
    _ENCODER = None


def count_tokens(line: str | None) -> int:
    """
    Counts the number of tokens in a text string.
    Uses tiktoken (cl100k_base) if available; otherwise falls back
    to a standard heuristic (~3.8 characters per token).
    """
    if not line:
        return 0

    if _ENCODER is not None:
        return len(_ENCODER.encode(line))

    # Lightweight heuristic fallback (zero-dependency)
    return max(1, int(len(line) / 3.8))


def count_message_tokens(message: dict[str, str]) -> int:
    """
    Counts tokens for a single chat turn: {"role": ..., "content": ...}
    Includes standard chat template framing overhead (~4 tokens for delimiters).
    """
    framing_overhead = 4
    role_tokens = count_tokens(message.get("role", ""))
    content_tokens = count_tokens(message.get("content", ""))
    return framing_overhead + role_tokens + content_tokens
