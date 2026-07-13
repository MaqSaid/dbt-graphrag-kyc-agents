"""Audit logging domain schemas for ISO 27001 compliance."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LLMInvocationMetadata(BaseModel):
    """Metadata captured from an LLM invocation for explainability.

    Records all details needed to reproduce and audit an LLM call,
    satisfying ISO 42001 AIMS requirements.
    """

    model_config = ConfigDict(strict=True)

    model_identifier: str
    model_version: str = ""
    prompt_template_hash: str = ""
    token_count_input: int = Field(default=0, ge=0)
    token_count_output: int = Field(default=0, ge=0)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    response_latency_ms: int = Field(default=0, ge=0)
    invocation_timestamp: datetime | None = None


class AuditLogEntry(BaseModel):
    """Immutable audit log entry with hash chain support."""

    model_config = ConfigDict(strict=True)

    entry_id: str
    evaluation_id: str
    event_type: str
    timestamp: datetime
    agent_name: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    model_identifier: str | None = None
    prompt_template_hash: str | None = None
    token_count_input: int | None = Field(default=None, ge=0)
    token_count_output: int | None = Field(default=None, ge=0)
    decision: str | None = None
    decision_rationale: str | None = None
    previous_hash: str = "GENESIS"
    entry_hash: str | None = None
