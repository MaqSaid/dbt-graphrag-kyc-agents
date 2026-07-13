"""Unit tests for the domain exception hierarchy."""

from __future__ import annotations

import pytest

from src.domain.exceptions import (
    AgentTimeoutError,
    GraphConnectionError,
    KYCEvaluationError,
    LLMConnectionError,
    SecurityViolationError,
    ValidationError,
)


class TestKYCEvaluationError:
    """Tests for the base KYCEvaluationError exception."""

    def test_message_only(self) -> None:
        err = KYCEvaluationError("something went wrong")
        assert str(err) == "something went wrong"
        assert err.message == "something went wrong"
        assert err.evaluation_id is None

    def test_with_evaluation_id(self) -> None:
        err = KYCEvaluationError("failure", evaluation_id="eval-123")
        assert err.evaluation_id == "eval-123"
        assert "[evaluation_id=eval-123]" in str(err)
        assert "failure" in str(err)

    def test_is_exception(self) -> None:
        err = KYCEvaluationError("test")
        assert isinstance(err, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(KYCEvaluationError, match="test error"):
            raise KYCEvaluationError("test error")


class TestAgentTimeoutError:
    """Tests for AgentTimeoutError."""

    def test_attributes(self) -> None:
        err = AgentTimeoutError(
            agent_name="Identity_Verifier", timeout_seconds=30
        )
        assert err.agent_name == "Identity_Verifier"
        assert err.timeout_seconds == 30
        assert err.evaluation_id is None

    def test_str_representation(self) -> None:
        err = AgentTimeoutError(
            agent_name="Graph_Analyst", timeout_seconds=20
        )
        assert "Graph_Analyst" in str(err)
        assert "20" in str(err)

    def test_with_evaluation_id(self) -> None:
        err = AgentTimeoutError(
            agent_name="Sanctions_Analyst",
            timeout_seconds=15,
            evaluation_id="eval-456",
        )
        assert err.evaluation_id == "eval-456"
        assert "[evaluation_id=eval-456]" in str(err)

    def test_inherits_from_base(self) -> None:
        err = AgentTimeoutError(agent_name="test", timeout_seconds=10)
        assert isinstance(err, KYCEvaluationError)
        assert isinstance(err, Exception)

    def test_can_be_caught_as_base(self) -> None:
        with pytest.raises(KYCEvaluationError):
            raise AgentTimeoutError(agent_name="test", timeout_seconds=5)


class TestGraphConnectionError:
    """Tests for GraphConnectionError."""

    def test_default_message(self) -> None:
        err = GraphConnectionError()
        assert "Graph database connection failed" in str(err)
        assert err.evaluation_id is None

    def test_custom_message(self) -> None:
        err = GraphConnectionError(
            message="Neo4j host unreachable", evaluation_id="eval-789"
        )
        assert "Neo4j host unreachable" in str(err)
        assert err.evaluation_id == "eval-789"

    def test_inherits_from_base(self) -> None:
        err = GraphConnectionError()
        assert isinstance(err, KYCEvaluationError)


class TestLLMConnectionError:
    """Tests for LLMConnectionError."""

    def test_default_message(self) -> None:
        err = LLMConnectionError()
        assert "LLM provider unreachable" in str(err)

    def test_custom_message_with_evaluation_id(self) -> None:
        err = LLMConnectionError(
            message="Bedrock throttled after 3 retries",
            evaluation_id="eval-abc",
        )
        assert "Bedrock throttled" in str(err)
        assert err.evaluation_id == "eval-abc"

    def test_inherits_from_base(self) -> None:
        err = LLMConnectionError()
        assert isinstance(err, KYCEvaluationError)


class TestSecurityViolationError:
    """Tests for SecurityViolationError."""

    def test_default_message(self) -> None:
        err = SecurityViolationError()
        assert "Security constraint violated" in str(err)

    def test_custom_message(self) -> None:
        err = SecurityViolationError(
            message="Prompt injection detected in customer name field",
            evaluation_id="eval-sec",
        )
        assert "Prompt injection detected" in str(err)
        assert err.evaluation_id == "eval-sec"

    def test_inherits_from_base(self) -> None:
        err = SecurityViolationError()
        assert isinstance(err, KYCEvaluationError)


class TestValidationError:
    """Tests for ValidationError."""

    def test_default_message(self) -> None:
        err = ValidationError()
        assert "Validation failed" in str(err)

    def test_custom_message(self) -> None:
        err = ValidationError(
            message="CustomerOnboardingPayload missing required field 'email'",
            evaluation_id="eval-val",
        )
        assert "missing required field" in str(err)
        assert err.evaluation_id == "eval-val"

    def test_inherits_from_base(self) -> None:
        err = ValidationError()
        assert isinstance(err, KYCEvaluationError)


class TestExceptionChaining:
    """Tests for proper Python exception chaining patterns."""

    def test_chaining_with_raise_from(self) -> None:
        original = ConnectionError("TCP reset")
        try:
            try:
                raise original
            except ConnectionError as e:
                raise GraphConnectionError(
                    message="Neo4j unavailable", evaluation_id="eval-chain"
                ) from e
        except GraphConnectionError as err:
            assert err.__cause__ is original
            assert err.evaluation_id == "eval-chain"

    def test_chaining_preserves_context(self) -> None:
        try:
            try:
                raise TimeoutError("socket timeout")
            except TimeoutError:
                raise AgentTimeoutError(
                    agent_name="Graph_Analyst", timeout_seconds=20
                ) from None
        except AgentTimeoutError as err:
            assert err.__cause__ is None
            assert err.__suppress_context__ is True
