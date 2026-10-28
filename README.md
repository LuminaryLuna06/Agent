# Shorekeeper Agent

A modular, token-budgeted AI agent with persistent SQLite memory and tick logging.

## Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.10+** | Runtime environment |
| **SQLAlchemy 2.0** | ORM & database modeling (`sqlite3`) |
| **Pydantic v2** | Hyperparameter schema & payload validation |
| **tiktoken** | Token calculation (`cl100k_base` with heuristic fallback) |
| **Requests / python-dotenv** | HTTP transport & environment variables |
| **OpenAI-Compatible LLM** | Backend inference server (e.g., Llama.cpp / vLLM) |

---

## Project Structure

```text
Agent
├── src/
│   ├── __init__.py           # Unified package exports
│   ├── agent/
│   │   ├── __init__.py
│   │   └── agent.py          # ShorekeeperAgent orchestrator & turn logic
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py       # Global environment constants & limits
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py         # SQLAlchemy models (Message, StateField, TickLog)
│   │   ├── repository.py     # Database CRUD transactions
│   │   └── session.py        # SQLite engine & SessionLocal lifecycle
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py         # HTTP inference client
│   │   └── config.py         # LLMConfig schema
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── builder.py        # System prompt & context-time message builders
│   │   └── templates.py      # Persona & voice anchors
│   └── tokens/
│       ├── __init__.py
│       ├── budget.py         # Dynamic budgeting & newest-first window fitting
│       └── counter.py        # Token counting logic
│
├── docs/
│   └── test_plan.md          # Architecture & testing roadmap
├── main.ipynb                # Interactive exploration notebook
├── main.py                   # Terminal chat runner
├── test.db                   # Local SQLite database
└── .env                      # Environment configuration (LLAMA_URL)
```

---

## Quick Start

1. **Install Dependencies**:
   ```bash
   uv pip install sqlalchemy pydantic tiktoken requests python-dotenv
   ```

2. **Configure Environment**:
   Create a `.env` file:
   ```env
   LLAMA_URL=http://localhost:8080/v1
   ```

3. **Run**:
   ```python
   from src import SessionLocal, ShorekeeperAgent

   with SessionLocal() as db:
       agent = ShorekeeperAgent(db=db)
       reply = agent.step("Hello Shorekeeper")
       print(reply)
   ```
