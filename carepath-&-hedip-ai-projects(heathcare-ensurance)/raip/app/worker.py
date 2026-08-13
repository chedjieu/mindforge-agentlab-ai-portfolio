"""Ingestion worker — polls SKIP LOCKED-style queued jobs."""

from __future__ import annotations

import logging
import time

from app.ingestion.pipeline import process_next_job
from app.observability.telemetry import setup_logging
from app.storage.db import get_session_factory, init_db

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()
    init_db()
    factory = get_session_factory()
    logger.info("RAIP ingestion worker started")
    while True:
        with factory() as session:
            try:
                did = process_next_job(session)
                session.commit()
            except Exception:
                session.rollback()
                logger.exception("job failed")
                did = True
        time.sleep(0.5 if did else 2.0)


if __name__ == "__main__":
    main()
