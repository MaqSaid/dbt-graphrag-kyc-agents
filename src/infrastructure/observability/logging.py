"""Structured JSON logging configuration using structlog.

Provides correlation-aware structured logging with standard fields
for every log entry: correlation_id, evaluation_id, agent_name,
timestamp, log_level, and event_type.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog

# Context variables for request-scoped correlation
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
evaluation_id_var: ContextVar[str] = ContextVar("evaluation_id", default="")
agent_name_var: ContextVar[str] = ContextVar("agent_name", default="")


def add_context_vars(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add context variables to every log entry.

    Args:
        logger: The logger instance.
        method_name: The logging method called.
        event_dict: Current event dictionary.

    Returns:
        Enriched event dictionary with context variables.
    """
    event_dict["correlation_id"] = correlation_id_var.get("")
    event_dict["evaluation_id"] = evaluation_id_var.get("")
    event_dict["agent_name"] = agent_name_var.get("")
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structured JSON logging for the application.

    Sets up structlog with JSON rendering, timestamp injection,
    log level processing, and context variable merging.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR).
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_context_vars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "") -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically module name).

    Returns:
        Bound structlog logger.
    """
    return structlog.get_logger(name)


def set_correlation_context(
    correlation_id: str = "",
    evaluation_id: str = "",
    agent_name: str = "",
) -> None:
    """Set correlation context for the current execution scope.

    Args:
        correlation_id: Request correlation identifier.
        evaluation_id: KYC evaluation identifier.
        agent_name: Current agent name.
    """
    if correlation_id:
        correlation_id_var.set(correlation_id)
    if evaluation_id:
        evaluation_id_var.set(evaluation_id)
    if agent_name:
        agent_name_var.set(agent_name)
