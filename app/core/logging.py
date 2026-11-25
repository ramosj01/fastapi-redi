import json
import logging
import sys
from contextvars import ContextVar

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    """Structured JSON logs so a log aggregator can correlate requests across replicas."""

    def __init__(self, instance_id: str) -> None:
        super().__init__()
        self.instance_id = instance_id

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "instance": self.instance_id,
            "request_id": request_id_ctx.get(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str, instance_id: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(instance_id))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
