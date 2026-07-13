"""Identity Verifier agent — Strands SDK agent for customer identity validation.

Implements the Identity_Verifier as a Strands agent with @tool-decorated functions
for email validation, phone validation, national ID validation, government registry
verification, and confidence score computation.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

try:
    from strands import Agent, tool
except ImportError:
    # Lightweight mock for development without strands-agents installed
    from typing import Callable, TypeVar

    F = TypeVar("F", bound=Callable[..., Any])

    def tool(func: F) -> F:
        """Mock @tool decorator preserving the original function."""
        func._is_tool = True  # type: ignore[attr-defined]  # noqa: SLF001
        return func

    class Agent:  # type: ignore[no-redef]
        """Mock Agent class matching Strands SDK interface."""

        def __init__(
            self,
            system_prompt: str = "",
            tools: list[Any] | None = None,
            max_iterations: int = 10,
            **kwargs: Any,
        ) -> None:
            """Initialize mock Agent.

            Args:
                system_prompt: System prompt for the agent.
                tools: List of tool functions available to the agent.
                max_iterations: Maximum reasoning iterations.
                **kwargs: Additional keyword arguments.
            """
            self.system_prompt = system_prompt
            self.tools = tools or []
            self.max_iterations = max_iterations


if TYPE_CHECKING:
    from domain.ports.customer_registry_port import CustomerRegistryPort
    from domain.ports.llm_client_port import LLMClientPort


@tool
def validate_email_format(email: str) -> dict[str, Any]:
    """Validate email address against RFC 5322 simplified format rules.

    Checks that the email conforms to the standard pattern:
    local-part@domain with valid characters and TLD of at least 2 characters.

    Args:
        email: Email address string to validate.

    Returns:
        Dictionary with keys:
            - field_name: "email"
            - is_valid: Whether the email passes validation
            - error_description: Error message if invalid, None otherwise
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern, email):
        return {
            "field_name": "email",
            "is_valid": True,
            "error_description": None,
        }
    return {
        "field_name": "email",
        "is_valid": False,
        "error_description": "Email does not conform to RFC 5322 format",
    }


@tool
def validate_phone_e164(phone: str) -> dict[str, Any]:
    """Validate phone number against E.164 international format.

    E.164 format requires a leading '+' followed by country code (1-3 digits)
    and subscriber number, with total length between 7 and 15 digits.

    Args:
        phone: Phone number string to validate.

    Returns:
        Dictionary with keys:
            - field_name: "phone"
            - is_valid: Whether the phone passes E.164 validation
            - error_description: Error message if invalid, None otherwise
    """
    if re.match(r"^\+[1-9]\d{6,14}$", phone):
        return {
            "field_name": "phone",
            "is_valid": True,
            "error_description": None,
        }
    return {
        "field_name": "phone",
        "is_valid": False,
        "error_description": "Phone number does not conform to E.164 format",
    }


@tool
def validate_national_id(national_id: str, country_code: str) -> dict[str, Any]:
    """Validate national identification number format for the given country.

    Performs structural validation ensuring the ID contains only alphanumeric
    characters and hyphens, and falls within acceptable length bounds (5-30 chars).

    Args:
        national_id: National identification number to validate.
        country_code: ISO 3166-1 alpha-2 country code (e.g., "US", "GB").

    Returns:
        Dictionary with keys:
            - field_name: "national_id"
            - is_valid: Whether the national ID passes format validation
            - country_code: The country code used for validation
            - error_description: Error message if invalid, None otherwise
    """
    if len(national_id) < 5 or len(national_id) > 30:
        return {
            "field_name": "national_id",
            "is_valid": False,
            "country_code": country_code,
            "error_description": "National ID must be between 5 and 30 characters",
        }
    if not re.match(r"^[a-zA-Z0-9\-]+$", national_id):
        return {
            "field_name": "national_id",
            "is_valid": False,
            "country_code": country_code,
            "error_description": (
                "National ID must contain only alphanumeric characters and hyphens"
            ),
        }
    return {
        "field_name": "national_id",
        "is_valid": True,
        "country_code": country_code,
        "error_description": None,
    }


@tool
def compute_confidence_score(field_validations: list[dict[str, Any]]) -> float:
    """Compute overall verification confidence from individual field validation results.

    Calculates the ratio of valid fields to total fields evaluated.
    Returns 0.0 if no validations are provided.

    Args:
        field_validations: List of field validation result dictionaries,
            each containing at minimum an "is_valid" boolean key.

    Returns:
        Confidence score between 0.0 and 1.0 representing the fraction
        of fields that passed validation.
    """
    if not field_validations:
        return 0.0
    valid_count = sum(1 for fv in field_validations if fv.get("is_valid", False))
    return valid_count / len(field_validations)


def _create_check_government_registry(
    registry_port: CustomerRegistryPort,
) -> Any:
    """Create a check_government_registry tool with the injected registry port.

    Uses the closure pattern to inject the CustomerRegistryPort dependency
    into the tool function without exposing it as a tool parameter.

    Args:
        registry_port: Injected port for government registry verification.

    Returns:
        A @tool-decorated function that calls the registry port.
    """
    @tool
    def check_government_registry(
        full_name: str,
        national_id: str,
        date_of_birth: str,
    ) -> dict[str, Any]:
        """Verify identity fields against government registry via CustomerRegistryPort.

        Calls the injected government registry port to verify that the provided
        identity information matches authoritative records.

        Args:
            full_name: Customer's full legal name.
            national_id: National identification number.
            date_of_birth: Date of birth in ISO 8601 format (YYYY-MM-DD).

        Returns:
            Dictionary with keys:
                - is_verified: Whether the registry confirmed the identity
                - checks: List of individual registry check results
                - registry_response_time_ms: Response time from registry
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in an async context, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(
                        asyncio.run,
                        registry_port.verify_identity(
                            full_name=full_name,
                            national_id=national_id,
                            date_of_birth=date_of_birth,
                        ),
                    ).result()
            else:
                result = loop.run_until_complete(
                    registry_port.verify_identity(
                        full_name=full_name,
                        national_id=national_id,
                        date_of_birth=date_of_birth,
                    ),
                )
        except RuntimeError:
            result = asyncio.run(
                registry_port.verify_identity(
                    full_name=full_name,
                    national_id=national_id,
                    date_of_birth=date_of_birth,
                ),
            )

        return {
            "is_verified": result.is_verified,
            "checks": [check.model_dump() for check in result.checks],
            "registry_response_time_ms": result.registry_response_time_ms,
        }

    return check_government_registry


_IDENTITY_VERIFIER_SYSTEM_PROMPT = """You are an identity verification specialist agent.

Your role is to validate customer onboarding identity data for structural correctness
and verify it against government registry sources. You systematically:

1. Validate email format against RFC 5322 rules
2. Validate phone numbers against E.164 international format
3. Validate national identification numbers for format compliance
4. Check identity claims against government registry databases
5. Compute an overall confidence score based on validation results

You process each field methodically and report detailed validation results.
When all validations are complete, compute the confidence score to summarize
the overall identity verification strength.

Always validate ALL fields before computing the confidence score.
If any field fails validation, include specific error descriptions.
"""


def create_identity_verifier_agent(
    registry_port: CustomerRegistryPort,
    llm_port: LLMClientPort,
) -> Agent:
    """Factory function creating the Identity_Verifier Strands agent.

    Creates a Strands Agent configured with identity verification tools
    and a specialized system prompt. Uses the closure pattern to inject
    the CustomerRegistryPort into the check_government_registry tool.

    Args:
        registry_port: Port implementation for government registry lookups.
        llm_port: Port implementation for LLM provider interactions.

    Returns:
        Configured Strands Agent with identity verification tools,
        max_iterations=10, and identity specialist system prompt.
    """
    check_registry_tool = _create_check_government_registry(registry_port)

    return Agent(
        system_prompt=_IDENTITY_VERIFIER_SYSTEM_PROMPT,
        tools=[
            validate_email_format,
            validate_phone_e164,
            validate_national_id,
            check_registry_tool,
            compute_confidence_score,
        ],
        max_iterations=10,
    )
