from __future__ import annotations

import os
from functools import wraps
from typing import Any

try:
    from langfuse import get_client as _get_langfuse_client
    from langfuse import observe as _langfuse_observe

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False
    _get_langfuse_client = None
    _langfuse_observe = None


class _DummyClient:
    def update_current_trace(self, **kwargs: Any) -> None:
        return None

    def update_current_generation(self, **kwargs: Any) -> None:
        return None

    def get_prompt(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Langfuse tracing is disabled")


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )


def observe(*args: Any, **kwargs: Any):
    if tracing_enabled() and _langfuse_observe is not None:
        return _langfuse_observe(*args, **kwargs)

    def decorator(func):
        @wraps(func)
        def wrapper(*func_args: Any, **func_kwargs: Any):
            return func(*func_args, **func_kwargs)

        return wrapper

    return decorator


def get_langfuse_client():
    if tracing_enabled() and _get_langfuse_client is not None:
        return _get_langfuse_client()
    return _DummyClient()


if _langfuse_observe is not None:
    observe.__module__ = _langfuse_observe.__module__
