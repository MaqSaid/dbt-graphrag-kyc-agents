"""Amazon Bedrock adapter implementing LLMClientPort.

Provides LLM text generation, structured output, and embeddings
via the AWS Bedrock runtime API with retry and circuit breaker.
"""

from __future__ import annotations

import json
import time

import boto3

from src.domain.exceptions import LLMConnectionError
from src.domain.ports.llm_client_port import LLMClientPort, LLMInvocationMetadata
from src.infrastructure.resilience.circuit_breaker import CircuitBreaker


class BedrockAdapter(LLMClientPort):
    """Amazon Bedrock implementation of LLMClientPort.

    Args:
        region: AWS region for Bedrock service.
    """

    def __init__(self, region: str = "us-east-1") -> None:
        """Initialize Bedrock adapter."""
        self._region = region
        self._client = boto3.client("bedrock-runtime", region_name=region)
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout_seconds=60,
            service_name="bedrock",
        )

    async def generate_text(
        self,
        model_identifier: str,
        prompt_text: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> tuple[str, LLMInvocationMetadata]:
        """Generate text completion via Bedrock.

        Args:
            model_identifier: Bedrock model ID.
            prompt_text: The prompt to send.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            Tuple of (generated_text, invocation_metadata).

        Raises:
            LLMConnectionError: If Bedrock is unreachable.
        """
        if not self._circuit_breaker.can_execute():
            msg = "Bedrock circuit breaker is open"
            raise LLMConnectionError(msg)

        start_time = time.monotonic()
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt_text}],
            })
            response = self._client.invoke_model(
                modelId=model_identifier,
                body=body,
                contentType="application/json",
            )
            response_body = json.loads(response["body"].read())
            generated_text = response_body["content"][0]["text"]
            input_tokens = response_body.get("usage", {}).get("input_tokens", 0)
            output_tokens = response_body.get("usage", {}).get("output_tokens", 0)

            latency_ms = int((time.monotonic() - start_time) * 1000)
            self._circuit_breaker.record_success()

            metadata = LLMInvocationMetadata(
                model_identifier=model_identifier,
                token_count_input=input_tokens,
                token_count_output=output_tokens,
                latency_ms=latency_ms,
            )
            return generated_text, metadata

        except Exception as exc:
            self._circuit_breaker.record_failure()
            msg = f"Bedrock generate_text failed: {exc}"
            raise LLMConnectionError(msg) from exc

    async def generate_structured(
        self,
        model_identifier: str,
        prompt_text: str,
        response_schema: type,
        temperature: float = 0.0,
    ) -> tuple[object, LLMInvocationMetadata]:
        """Generate structured output validated against a Pydantic schema.

        Args:
            model_identifier: Bedrock model ID.
            prompt_text: The prompt with JSON output instructions.
            response_schema: Pydantic model class for validation.
            temperature: Sampling temperature.

        Returns:
            Tuple of (validated_model_instance, invocation_metadata).

        Raises:
            LLMConnectionError: If Bedrock is unreachable.
        """
        schema_json = response_schema.model_json_schema()
        enhanced_prompt = (
            f"{prompt_text}\n\n"
            f"Respond with valid JSON matching this schema:\n"
            f"{json.dumps(schema_json, indent=2)}"
        )
        text, metadata = await self.generate_text(
            model_identifier, enhanced_prompt, temperature
        )
        # Parse and validate against schema
        parsed = json.loads(text)
        validated = response_schema.model_validate(parsed)
        return validated, metadata

    async def get_embeddings(
        self, model_identifier: str, texts: list[str]
    ) -> list[list[float]]:
        """Generate embeddings via Bedrock.

        Args:
            model_identifier: Embedding model ID.
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.

        Raises:
            LLMConnectionError: If Bedrock is unreachable.
        """
        if not self._circuit_breaker.can_execute():
            msg = "Bedrock circuit breaker is open"
            raise LLMConnectionError(msg)

        embeddings: list[list[float]] = []
        try:
            for text in texts:
                body = json.dumps({"inputText": text})
                response = self._client.invoke_model(
                    modelId=model_identifier,
                    body=body,
                    contentType="application/json",
                )
                response_body = json.loads(response["body"].read())
                embeddings.append(response_body["embedding"])
            self._circuit_breaker.record_success()
            return embeddings
        except Exception as exc:
            self._circuit_breaker.record_failure()
            msg = f"Bedrock get_embeddings failed: {exc}"
            raise LLMConnectionError(msg) from exc
