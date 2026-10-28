from sqlalchemy.orm import Session

from src.config.settings import CONTEXT_WINDOW
from src.db.repository import get_recent_messages, log_tick, save_message
from src.llm.client import llm_call
from src.llm.config import LLMConfig
from src.prompts.builder import build_message, build_system_prompt
from src.tokens.budget import dynamic_budget, fit_newest_first


class ShorekeeperAgent:
    """Orchestrates conversational turns and memory management."""

    def __init__(
        self,
        db: Session,
        config: LLMConfig | None = None,
        context_window: int = CONTEXT_WINDOW,
    ):
        self.db = db
        self.config = config or LLMConfig(
            model="Gemma4-12B",
            enable_thinking=True,
            reasoning_effort="medium",
        )
        self.budget = dynamic_budget(budget=context_window)
        if not self.budget:
            raise ValueError("Not enough Budget to start")

        self.system_prompt = build_system_prompt(
            budget=self.budget["persona"] + self.budget["anchor"]
        )
        if not self.system_prompt:
            raise ValueError("System prompt budget not enough")

        # Load recent messages and fit to budget
        recent = get_recent_messages(db=self.db, limit=100)
        self.messages = [{"role": m.role, "content": m.content} for m in recent]
        self.messages = fit_newest_first(
            messages=self.messages, budget=self.budget["chat"]
        )

    def step(self, user_msg: str) -> str | None:
        """Executes a single conversational turn."""
        user_record = save_message(db=self.db, role="user", content=user_msg)
        self.messages = build_message(history=self.messages, user_msg=user_msg)
        self.messages = fit_newest_first(
            messages=self.messages, budget=self.budget["chat"]
        )

        all_prompt_messages = self.system_prompt + self.messages
        response, reasoning = llm_call(messages=all_prompt_messages, config=self.config)
        if not response:
            return None

        save_message(db=self.db, role="assistant", content=response)
        self.messages.append({"role": "assistant", "content": response})

        full_prompt_text = "\n\n".join(
            f"[{msg['role'].upper()}]:\n{msg['content']}" for msg in all_prompt_messages
        )

        if user_record:
            log_tick(
                db=self.db,
                trigger="user_message",
                last_msg_id=user_record.id,
                prompt=full_prompt_text,
                output=response,
                thinking=reasoning,
                params=self.config,
            )

        return response
