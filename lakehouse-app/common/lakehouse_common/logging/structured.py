"""JSON-structured logger compatible with Azure Log Analytics ingestion."""
from __future__ import annotations

import logging
import os
import structlog


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a structured logger. Call once per module."""
    if not structlog.is_configured():
        _configure()
    return structlog.get_logger(name)


def _configure() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
    )
