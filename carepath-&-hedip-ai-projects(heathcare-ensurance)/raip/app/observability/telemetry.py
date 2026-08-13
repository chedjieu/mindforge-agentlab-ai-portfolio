"""Structured logging, correlation IDs, redaction, and Prometheus-ish metrics."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from contextvars import ContextVar
from typing import Any

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
tenant_id_ctx: ContextVar[str] = ContextVar("tenant_id", default="")

_REDACT = re.compile(
    r"\b(\d{3}-\d{2}-\d{4}|\d{9}|\+?1?\d{10})\b|(mrn|ssn|dob)\s*[:=]\s*\S+",
    re.IGNORECASE,
)

_counters: dict[str, float] = defaultdict(float)
_gauges: dict[str, float] = {}


def redact(text: str) -> str:
    return _REDACT.sub("[REDACTED]", text)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s tenant=%(tenant)s %(message)s",
    )
    old = logging.getLogRecordFactory()

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = old(*args, **kwargs)
        record.request_id = request_id_ctx.get("")
        record.tenant = tenant_id_ctx.get("")
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        return record

    logging.setLogRecordFactory(factory)


def incr(name: str, value: float = 1.0) -> None:
    _counters[name] += value


def gauge(name: str, value: float) -> None:
    _gauges[name] = value


def prometheus_text() -> str:
    lines = ["# RAIP metrics — local scrape format"]
    for k, v in sorted(_counters.items()):
        lines.append(f"raip_{k} {v}")
    for k, v in sorted(_gauges.items()):
        lines.append(f"raip_{k} {v}")
    return "\n".join(lines) + "\n"


def estimate_cost(input_tokens: int, output_tokens: int, in_rate: float, out_rate: float) -> float:
    return (input_tokens / 1000.0) * in_rate + (output_tokens / 1000.0) * out_rate
