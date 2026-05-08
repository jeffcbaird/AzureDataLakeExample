"""Structured logging for the ingestion Function App.

Thin wrapper around ``lakehouse_common.logging.structured`` that binds
``component="ingestion"`` to every log line so Log Analytics queries can
filter to this app without knowing individual logger names.

Usage::

    from shared.logging import get_logger

    log = get_logger("sales")
    log.info("ingestion.start", date="2024-01-15")
"""
from __future__ import annotations

import structlog
from lakehouse_common.logging.structured import get_logger as _base_get_logger


def get_logger(source: str) -> structlog.BoundLogger:
    """Return a structlog logger bound with *source* and ``component='ingestion'``."""
    return _base_get_logger(__name__).bind(source=source, component="ingestion")
