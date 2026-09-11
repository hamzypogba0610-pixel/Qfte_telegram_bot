"""
QFTE V13 — Configuration du logging avec structlog
"""

import logging
import sys
import structlog

from config import LOG_LEVEL


def setup_logging():
    """Configure structlog + logging standard."""

    # Niveau de log
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    # Handler console
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Config logging de base
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        handlers=[handler],
    )

    # Config structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()
