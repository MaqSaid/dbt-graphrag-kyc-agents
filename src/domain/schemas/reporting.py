"""Compliance reporting domain schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExplainabilitySchema(BaseModel):
    """ISO 42001 AIMS compliance metadata for LLM invocations."""

    model_config = ConfigDict(strict=True)

    prompt_template_hash: str
    model_identifier: str
    model_version: str
    token_count_input: int = Field(ge=0)
    token_count_output: int = Field(ge=0)
    temperature_setting: float = Field(ge=0.0, le=2.0)
    invocation_timestamp: datetime
    trace_mapping: dict[str, list[str]]


class ReportSection(BaseModel):
    """A single section within a compliance report."""

    model_config = ConfigDict(strict=True)

    section_title: str
    content: str
    source_references: list[str]
    explainability: ExplainabilitySchema


class ComplianceReport(BaseModel):
    """Complete compliance audit report for a KYC evaluation."""

    model_config = ConfigDict(strict=True)

    report_id: str
    evaluation_id: str
    generation_timestamp: datetime
    pipeline_version: str
    executive_summary: ReportSection
    identity_findings: ReportSection
    sanctions_findings: ReportSection
    network_findings: ReportSection
    risk_assessment: ReportSection
    recommended_action: str
    escalation_ambiguities: list[str] | None = None
