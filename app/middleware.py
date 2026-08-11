from __future__ import annotations

import time
import uuid
from typing import Any

from starlette.datastructures import Headers, MutableHeaders
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        clear_contextvars()

        incoming_request_id = (Headers(scope=scope).get("x-request-id") or "").strip()
        if incoming_request_id.startswith("req-") and len(incoming_request_id) >= 12:
            correlation_id = incoming_request_id
        else:
            correlation_id = f"req-{uuid.uuid4().hex[:8]}"

        bind_contextvars(correlation_id=correlation_id)
        scope.setdefault("state", {})["correlation_id"] = correlation_id

        start = time.perf_counter()

        async def send_with_correlation_headers(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                latency_ms = int((time.perf_counter() - start) * 1000)
                headers = MutableHeaders(scope=message)
                headers["x-request-id"] = correlation_id
                headers["x-response-time-ms"] = str(latency_ms)
            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation_headers)
        finally:
            clear_contextvars()
