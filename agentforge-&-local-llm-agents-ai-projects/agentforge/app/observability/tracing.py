from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from app.config import get_settings

logger = logging.getLogger("agentforge.tracing")

_tracer = None
_initialized = False


def setup_tracing() -> None:
    """Initialize OpenTelemetry and optional Langfuse hooks."""
    global _tracer, _initialized
    if _initialized:
        return

    settings = get_settings()
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )

        resource = Resource.create({"service.name": settings.otel_service_name})
        provider = TracerProvider(resource=resource)

        if settings.otel_exporter_otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        else:
            # Lightweight local visibility without requiring a collector
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(settings.otel_service_name)
    except Exception as exc:  # pragma: no cover
        logger.warning("OpenTelemetry setup skipped: %s", exc)
        _tracer = None

    if settings.langfuse_public_key and settings.langfuse_secret_key:
        logger.info(
            "Langfuse credentials detected (host=%s). "
            "Wire SDK callbacks in your deployment if desired.",
            settings.langfuse_host,
        )

    _initialized = True


@contextmanager
def traced_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[None]:
    setup_tracing()
    if _tracer is None:
        yield
        return

    from opentelemetry import trace

    with _tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        try:
            yield
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            raise
