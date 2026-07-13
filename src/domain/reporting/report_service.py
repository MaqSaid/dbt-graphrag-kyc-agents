"""Compliance report generation domain service.

Assembles KYC evaluation results into a structured compliance report with
explainability metadata for the Reporting bounded context.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from domain.schemas.reporting import (
    ComplianceReport,
    ExplainabilitySchema,
    ReportSection,
)

if TYPE_CHECKING:
    from domain.ports.llm_client_port import LLMClientPort
    from domain.schemas.kyc_state import KYCState


class ComplianceReportService:
    """Domain service for compliance report generation.

    Assembles all agent results from the KYC evaluation state into
    structured report sections, generates trace mappings for
    explainability, and produces the final compliance report using
    the LLM client port.

    Args:
        llm_port: Injected port for LLM text generation.
    """

    #: Default LLM model for report generation
    _DEFAULT_MODEL: str = "anthropic.claude-sonnet-4-20250514"

    #: Pipeline version for report metadata
    _PIPELINE_VERSION: str = "1.0.0"

    def __init__(self, llm_port: LLMClientPort) -> None:
        """Initialize with injected LLMClientPort.

        Args:
            llm_port: Port implementation for LLM provider interactions.
        """
        self._llm_port = llm_port

    async def generate_report(
        self,
        state: KYCState,
    ) -> ComplianceReport:
        """Generate a complete compliance report from KYC evaluation state.

        Assembles identity, sanctions, graph, and risk assessment findings
        into structured report sections, each with LLM-generated narratives
        and explainability metadata linking assertions to source data.

        Args:
            state: Complete KYC evaluation state with all agent results.

        Returns:
            Structured compliance report with explainability metadata.
        """
        report_id = str(uuid.uuid4())
        generation_timestamp = datetime.now(UTC)

        # Generate each report section via LLM
        executive_summary = await self._generate_executive_summary(state)
        identity_findings = await self._generate_identity_findings(state)
        sanctions_findings = await self._generate_sanctions_findings(state)
        network_findings = await self._generate_network_findings(state)
        risk_assessment = await self._generate_risk_assessment(state)

        # Determine recommended action
        recommended_action = self._determine_recommended_action(state)

        # Identify any ambiguities requiring escalation
        escalation_ambiguities = self._identify_escalation_ambiguities(state)

        return ComplianceReport(
            report_id=report_id,
            evaluation_id=state.evaluation_id,
            generation_timestamp=generation_timestamp,
            pipeline_version=self._PIPELINE_VERSION,
            executive_summary=executive_summary,
            identity_findings=identity_findings,
            sanctions_findings=sanctions_findings,
            network_findings=network_findings,
            risk_assessment=risk_assessment,
            recommended_action=recommended_action,
            escalation_ambiguities=escalation_ambiguities or None,
        )

    async def _generate_executive_summary(
        self,
        state: KYCState,
    ) -> ReportSection:
        """Generate the executive summary section.

        Args:
            state: KYC evaluation state.

        Returns:
            ReportSection with executive summary content.
        """
        prompt = self._build_executive_summary_prompt(state)
        content, metadata = await self._llm_port.generate_text(
            model_identifier=self._DEFAULT_MODEL,
            prompt_text=prompt,
            temperature=0.0,
        )

        trace_mapping = self._build_trace_mapping(
            section="executive_summary",
            state=state,
        )

        explainability = ExplainabilitySchema(
            prompt_template_hash=hashlib.sha256(prompt.encode()).hexdigest(),
            model_identifier=metadata.model_identifier,
            model_version=metadata.model_version,
            token_count_input=metadata.token_count_input,
            token_count_output=metadata.token_count_output,
            temperature_setting=metadata.temperature,
            invocation_timestamp=metadata.invocation_timestamp,
            trace_mapping=trace_mapping,
        )

        return ReportSection(
            section_title="Executive Summary",
            content=content,
            source_references=[state.evaluation_id],
            explainability=explainability,
        )

    async def _generate_identity_findings(
        self,
        state: KYCState,
    ) -> ReportSection:
        """Generate the identity verification findings section.

        Args:
            state: KYC evaluation state.

        Returns:
            ReportSection with identity findings content.
        """
        prompt = self._build_identity_findings_prompt(state)
        content, metadata = await self._llm_port.generate_text(
            model_identifier=self._DEFAULT_MODEL,
            prompt_text=prompt,
            temperature=0.0,
        )

        trace_mapping = self._build_trace_mapping(
            section="identity_findings",
            state=state,
        )

        explainability = ExplainabilitySchema(
            prompt_template_hash=hashlib.sha256(prompt.encode()).hexdigest(),
            model_identifier=metadata.model_identifier,
            model_version=metadata.model_version,
            token_count_input=metadata.token_count_input,
            token_count_output=metadata.token_count_output,
            temperature_setting=metadata.temperature,
            invocation_timestamp=metadata.invocation_timestamp,
            trace_mapping=trace_mapping,
        )

        return ReportSection(
            section_title="Identity Verification Findings",
            content=content,
            source_references=self._get_identity_source_refs(state),
            explainability=explainability,
        )

    async def _generate_sanctions_findings(
        self,
        state: KYCState,
    ) -> ReportSection:
        """Generate the sanctions screening findings section.

        Args:
            state: KYC evaluation state.

        Returns:
            ReportSection with sanctions findings content.
        """
        prompt = self._build_sanctions_findings_prompt(state)
        content, metadata = await self._llm_port.generate_text(
            model_identifier=self._DEFAULT_MODEL,
            prompt_text=prompt,
            temperature=0.0,
        )

        trace_mapping = self._build_trace_mapping(
            section="sanctions_findings",
            state=state,
        )

        explainability = ExplainabilitySchema(
            prompt_template_hash=hashlib.sha256(prompt.encode()).hexdigest(),
            model_identifier=metadata.model_identifier,
            model_version=metadata.model_version,
            token_count_input=metadata.token_count_input,
            token_count_output=metadata.token_count_output,
            temperature_setting=metadata.temperature,
            invocation_timestamp=metadata.invocation_timestamp,
            trace_mapping=trace_mapping,
        )

        return ReportSection(
            section_title="Sanctions Screening Findings",
            content=content,
            source_references=self._get_sanctions_source_refs(state),
            explainability=explainability,
        )

    async def _generate_network_findings(
        self,
        state: KYCState,
    ) -> ReportSection:
        """Generate the network/graph analysis findings section.

        Args:
            state: KYC evaluation state.

        Returns:
            ReportSection with network findings content.
        """
        prompt = self._build_network_findings_prompt(state)
        content, metadata = await self._llm_port.generate_text(
            model_identifier=self._DEFAULT_MODEL,
            prompt_text=prompt,
            temperature=0.0,
        )

        trace_mapping = self._build_trace_mapping(
            section="network_findings",
            state=state,
        )

        explainability = ExplainabilitySchema(
            prompt_template_hash=hashlib.sha256(prompt.encode()).hexdigest(),
            model_identifier=metadata.model_identifier,
            model_version=metadata.model_version,
            token_count_input=metadata.token_count_input,
            token_count_output=metadata.token_count_output,
            temperature_setting=metadata.temperature,
            invocation_timestamp=metadata.invocation_timestamp,
            trace_mapping=trace_mapping,
        )

        return ReportSection(
            section_title="Network Analysis Findings",
            content=content,
            source_references=self._get_graph_source_refs(state),
            explainability=explainability,
        )

    async def _generate_risk_assessment(
        self,
        state: KYCState,
    ) -> ReportSection:
        """Generate the risk assessment section.

        Args:
            state: KYC evaluation state.

        Returns:
            ReportSection with risk assessment content.
        """
        prompt = self._build_risk_assessment_prompt(state)
        content, metadata = await self._llm_port.generate_text(
            model_identifier=self._DEFAULT_MODEL,
            prompt_text=prompt,
            temperature=0.0,
        )

        trace_mapping = self._build_trace_mapping(
            section="risk_assessment",
            state=state,
        )

        explainability = ExplainabilitySchema(
            prompt_template_hash=hashlib.sha256(prompt.encode()).hexdigest(),
            model_identifier=metadata.model_identifier,
            model_version=metadata.model_version,
            token_count_input=metadata.token_count_input,
            token_count_output=metadata.token_count_output,
            temperature_setting=metadata.temperature,
            invocation_timestamp=metadata.invocation_timestamp,
            trace_mapping=trace_mapping,
        )

        return ReportSection(
            section_title="Risk Assessment",
            content=content,
            source_references=[state.evaluation_id],
            explainability=explainability,
        )

    @staticmethod
    def _build_executive_summary_prompt(state: KYCState) -> str:
        """Build prompt for executive summary generation.

        Args:
            state: KYC evaluation state.

        Returns:
            Formatted prompt string.
        """
        identity_status = (
            state.identity_verification_result.verification_status
            if state.identity_verification_result
            else "not_evaluated"
        )
        sanctions_status = (
            state.sanctions_screening_result.status
            if state.sanctions_screening_result
            else "not_evaluated"
        )
        graph_status = (
            state.graph_analysis_result.status
            if state.graph_analysis_result
            else "not_evaluated"
        )

        return (
            f"Generate a concise executive summary for KYC evaluation "
            f"{state.evaluation_id}.\n"
            f"Identity verification status: {identity_status}\n"
            f"Sanctions screening status: {sanctions_status}\n"
            f"Graph analysis status: {graph_status}\n"
            f"Final decision: {state.final_decision.value}\n"
            f"Summarize key findings and recommended action in 2-3 paragraphs."
        )

    @staticmethod
    def _build_identity_findings_prompt(state: KYCState) -> str:
        """Build prompt for identity findings section.

        Args:
            state: KYC evaluation state.

        Returns:
            Formatted prompt string.
        """
        if not state.identity_verification_result:
            return "No identity verification result available. State this clearly."

        result = state.identity_verification_result
        field_summary = ", ".join(
            f"{fv.field_name}={'PASS' if fv.is_valid else 'FAIL'}"
            for fv in result.field_validations
        )

        return (
            f"Describe identity verification findings for evaluation "
            f"{state.evaluation_id}.\n"
            f"Status: {result.verification_status}\n"
            f"Confidence score: {result.confidence_score:.2f}\n"
            f"Field validations: {field_summary}\n"
            f"Registry checks: {len(result.registry_checks)} performed\n"
            f"Provide a detailed narrative of the verification process and findings."
        )

    @staticmethod
    def _build_sanctions_findings_prompt(state: KYCState) -> str:
        """Build prompt for sanctions findings section.

        Args:
            state: KYC evaluation state.

        Returns:
            Formatted prompt string.
        """
        if not state.sanctions_screening_result:
            return "No sanctions screening result available. State this clearly."

        result = state.sanctions_screening_result
        return (
            f"Describe sanctions screening findings for evaluation "
            f"{state.evaluation_id}.\n"
            f"Status: {result.status}\n"
            f"Match score: {result.match_score:.2f}\n"
            f"Number of matches: {len(result.matches)}\n"
            f"Confirmed match: {result.has_confirmed_match}\n"
            f"Sources screened: {', '.join(result.sources_screened)}\n"
            f"Provide a detailed narrative of the screening process and findings."
        )

    @staticmethod
    def _build_network_findings_prompt(state: KYCState) -> str:
        """Build prompt for network analysis findings section.

        Args:
            state: KYC evaluation state.

        Returns:
            Formatted prompt string.
        """
        if not state.graph_analysis_result:
            return "No graph analysis result available. State this clearly."

        result = state.graph_analysis_result
        return (
            f"Describe graph network analysis findings for evaluation "
            f"{state.evaluation_id}.\n"
            f"Status: {result.status}\n"
            f"Network risk score: {result.network_risk_score:.4f}\n"
            f"Discovered paths: {len(result.discovered_paths)}\n"
            f"Flagged entities: {len(result.connected_flagged_entities)}\n"
            f"Confirmed fraud ring: {result.has_confirmed_fraud_ring}\n"
            f"Provide a detailed narrative of the network traversal and findings."
        )

    @staticmethod
    def _build_risk_assessment_prompt(state: KYCState) -> str:
        """Build prompt for risk assessment section.

        Args:
            state: KYC evaluation state.

        Returns:
            Formatted prompt string.
        """
        identity_score = (
            state.identity_verification_result.confidence_score
            if state.identity_verification_result
            else 0.0
        )
        sanctions_score = (
            state.sanctions_screening_result.match_score
            if state.sanctions_screening_result
            else 0.0
        )
        network_score = (
            state.graph_analysis_result.network_risk_score
            if state.graph_analysis_result
            else 0.0
        )

        return (
            f"Generate a risk assessment for KYC evaluation "
            f"{state.evaluation_id}.\n"
            f"Identity confidence: {identity_score:.2f}\n"
            f"Sanctions match score: {sanctions_score:.2f}\n"
            f"Network risk score: {network_score:.4f}\n"
            f"Final decision: {state.final_decision.value}\n"
            f"Provide a comprehensive risk narrative with contributing factors."
        )

    @staticmethod
    def _build_trace_mapping(
        section: str,
        state: KYCState,
    ) -> dict[str, list[str]]:
        """Build trace mapping linking report assertions to source node IDs.

        Args:
            section: Report section identifier.
            state: KYC evaluation state.

        Returns:
            Dictionary mapping assertion keys to source node identifiers.
        """
        trace: dict[str, list[str]] = {}

        if section == "executive_summary":
            trace["overall_decision"] = [state.evaluation_id]

        if section == "identity_findings" and state.identity_verification_result:
            trace["identity_verification"] = [
                f"field:{fv.field_name}"
                for fv in state.identity_verification_result.field_validations
            ]
            trace["registry_checks"] = [
                f"registry:{rc.field_name}"
                for rc in state.identity_verification_result.registry_checks
            ]

        if section == "sanctions_findings" and state.sanctions_screening_result:
            trace["sanctions_matches"] = [
                f"match:{m.matched_entity.entity_name}"
                for m in state.sanctions_screening_result.matches
            ]
            trace["sources_screened"] = state.sanctions_screening_result.sources_screened

        if section == "network_findings" and state.graph_analysis_result:
            trace["flagged_entities"] = [
                f"node:{n.entity_id}"
                for n in state.graph_analysis_result.connected_flagged_entities
            ]
            trace["discovered_paths"] = [
                f"path:{i}"
                for i in range(len(state.graph_analysis_result.discovered_paths))
            ]

        if section == "risk_assessment":
            trace["risk_factors"] = [state.evaluation_id]

        return trace

    @staticmethod
    def _determine_recommended_action(state: KYCState) -> str:
        """Determine the recommended action based on final decision.

        Args:
            state: KYC evaluation state.

        Returns:
            Human-readable recommended action string.
        """
        decision_map = {
            "APPROVE": "Approve customer onboarding - proceed with account creation",
            "DENY": "Deny customer onboarding - flag for regulatory reporting",
            "ESCALATE_TO_HUMAN_REVIEW": (
                "Escalate to human compliance officer for manual review"
            ),
            "PENDING": "Evaluation incomplete - awaiting further agent results",
        }
        return decision_map.get(
            state.final_decision.value,
            "Unknown decision state - escalate to supervisor",
        )

    @staticmethod
    def _identify_escalation_ambiguities(state: KYCState) -> list[str]:
        """Identify ambiguities that warrant human review escalation.

        Args:
            state: KYC evaluation state.

        Returns:
            List of ambiguity descriptions, empty if none found.
        """
        ambiguities: list[str] = []

        if (
            state.identity_verification_result
            and state.identity_verification_result.verification_status == "ambiguous"
        ):
            ambiguities.append(
                "Identity verification returned ambiguous status - "
                "manual document review recommended",
            )

        if (
            state.sanctions_screening_result
            and state.sanctions_screening_result.status == "screening_ambiguous"
        ):
            ambiguities.append(
                "Sanctions screening returned ambiguous matches - "
                "manual entity resolution required",
            )

        if (
            state.graph_analysis_result
            and state.graph_analysis_result.has_confirmed_fraud_ring
        ):
            ambiguities.append(
                "Confirmed fraud ring pattern detected - "
                "investigation team review required",
            )

        return ambiguities

    @staticmethod
    def _get_identity_source_refs(state: KYCState) -> list[str]:
        """Get source references for identity findings section.

        Args:
            state: KYC evaluation state.

        Returns:
            List of source reference identifiers.
        """
        refs = [state.evaluation_id]
        if state.identity_verification_result:
            refs.extend(
                f"field:{fv.field_name}"
                for fv in state.identity_verification_result.field_validations
            )
        return refs

    @staticmethod
    def _get_sanctions_source_refs(state: KYCState) -> list[str]:
        """Get source references for sanctions findings section.

        Args:
            state: KYC evaluation state.

        Returns:
            List of source reference identifiers.
        """
        refs = [state.evaluation_id]
        if state.sanctions_screening_result:
            refs.extend(state.sanctions_screening_result.sources_screened)
        return refs

    @staticmethod
    def _get_graph_source_refs(state: KYCState) -> list[str]:
        """Get source references for graph findings section.

        Args:
            state: KYC evaluation state.

        Returns:
            List of source reference identifiers.
        """
        refs = [state.evaluation_id]
        if state.graph_analysis_result:
            refs.extend(
                f"node:{n.entity_id}"
                for n in state.graph_analysis_result.connected_flagged_entities
            )
        return refs
