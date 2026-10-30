import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.models import Base
from src.llm.config import LLMConfig


@pytest.fixture
def in_memory_db() -> Session:
    """Provides an isolated in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_llm_config() -> LLMConfig:
    """Provides a sample LLMConfig instance for testing."""
    return LLMConfig(
        model="test-gemma",
        enable_thinking=True,
        reasoning_effort="medium",
        temperature=0.7,
    )


@pytest.fixture
def mock_llm_response(monkeypatch):
    """Factory fixture to mock requests.post responses for llm_call."""

    def _mock(
        content: str = "The tides are steady, Rover.",
        reasoning: str | None = None,
        status_code: int = 200,
    ):
        class MockResponse:
            def __init__(self):
                self.status_code = status_code
                self.text = "OK" if status_code == 200 else f"Error {status_code}"

            def json(self):
                choice = {"message": {"content": content}}
                if reasoning is not None:
                    choice["message"]["reasoning_content"] = reasoning
                return {"choices": [choice]}

            def raise_for_status(self):
                if self.status_code >= 400:
                    import requests

                    raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

        mock_resp = MockResponse()
        monkeypatch.setattr("requests.post", lambda *args, **kwargs: mock_resp)
        return mock_resp

    return _mock
