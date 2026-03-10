"""structlog configuration for licit."""

import logging

import structlog


def setup_logging(verbose: bool = False) -> None:
    """Configure structlog for console output.

    Args:
        verbose: If True, set log level to DEBUG. Otherwise WARNING.
    """
    log_level = logging.DEBUG if verbose else logging.WARNING

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=False,
    )
