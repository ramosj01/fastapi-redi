import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_ctx

logger = logging.getLogger("app.access")


class RequestContextMiddleware:
    """Propagates X-Request-ID across services and tags responses with the replica id."""

    def __init__(self, app: ASGIApp, instance_id: str) -> None:
        self.app = app
        self.instance_id = instance_id

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        request_id = headers.get(b"x-request-id", b"").decode() or uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message.setdefault("headers", [])
                message["headers"] += [
                    (b"x-request-id", request_id.encode()),
                    (b"x-instance-id", self.instance_id.encode()),
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            logger.info(
                "%s %s %s %.1fms",
                scope["method"],
                scope["path"],
                status_code,
                (time.perf_counter() - start) * 1000,
            )
            request_id_ctx.reset(token)
