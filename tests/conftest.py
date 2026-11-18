"""Shared test fixtures and environment setup."""

import os

os.environ.setdefault("GOOGLE_API_KEY", "test-dummy-key-for-unit-tests")
os.environ.setdefault("GEMINI_MODEL", "gemini-3.5-flash-lite")
os.environ.setdefault("CHROMA_HOST", "localhost")
os.environ.setdefault("CHROMA_PORT", "8000")

import pytest


@pytest.fixture(autouse=True)
def _reset_tracing():
    from notifai.observability.tracing import reset_traces

    reset_traces()
    yield
    reset_traces()