"""OpenAI-compatible adapter implementing LLMClientPort.

Provides text generation, structured output, and embedding operations
via the OpenAI-compatible REST API using httpx (no openai package dependency).
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import httpx

from src.domain.exceptions import LLMConnectionError
from src.domain.schemas.audit import LLMInvocationMetadata
from src.infrastructure.resilience.circuit_breaker import CircuitBreaker
from src.infrastructure.resilience.retry import retry_with_backoff

if TYPE_CHECKING:
    from pydantic import BaseModel

    from src.domain.ports.llm_client_port import LLMClientPort


class _RateLimitError(Exception):
    """Internal exception for rate limit responses (HTTP 429)."""


class OpenAIAdapter:
    """Adapter for OpenAI-compatible LLM providers.

    Implements the LLMClientPort interface using httpx.AsyncClient for
    direct HTTP calls to the OpenAI API (or any compatible endpoint).
    Includes retry logic, circuit breaker, and metadata capture.

    Args:
        api_key: OpenAI API key for authentication.
        base_url: Optional base URL for the API (defaults to OpenAI's endpoint).
        failure_threshold: Circuit breaker failure threshold before opening.
        recovery_timeout_seconds: Seconds before circuit breaker transitions to half-open.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
    ) -> None:
        """Initialize the OpenAI adapter.

        Args:
            api_key: API key for OpenAI authentication.
            base_url: Base URL for the API endpoint. Defaults to https://api.openai.com/v1.
            failure_threshold: Number of failures before circuit opens.
            recovery_timeout_seconds: Recovery timeout for circuit breaker.
        """
        self._api_key = api_key
        self._base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout_seconds=recovery_timeout_seconds,
            service_name="openai",
        )
        self._http_client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(60.0, connect=10.0),
        )

    async def generate_text(
        self,
        model_identifier: str,
        prompt_text: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> tuple[str, LLMInvocationMetadata]:
        """Generate text completion via OpenAI-compatible API with metadata.

        Args:
            model_identifier: Model ID (e.g., "gpt-4", "gpt-3.5-turbo").
            prompt_text: The prompt to send to the model.
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Maximum tokens in the response.

        Returns:
            Tuple of (generated_text, invocation_metadata).

        Raises:
            LLMConnectionError: When API is unreachable after retries or circuit is open.
        """
        if not self._circuit_breaker.can_execute():
            raise LLMConnectionError(
                message=f"Circuit breaker OPEN for OpenAI service at {self._base_url}"
            )

        start_time = time.monotonic()
        invocation_timestamp = datetime.now(tz=timezone.utc)

        try:
            response_data = await self._chat_completion_with_retry(
                model_identifier=model_identifier,
                prompt_text=prompt_text,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self._circuit_breaker.record_success()
        except (_RateLimitError, httpx.HTTPError) as exc:
            self._circuit_breaker.record_failure()
            raise LLMConnectionError(
                message=f"OpenAI API call failed after retries: {exc}"
            ) from exc

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        generated_text = self._extract_text_from_response(response_data)
        token_input, token_output = self._extract_token_counts(response_data)
        model_version = self._extract_model_version(response_data, model_identifier)

        metadata = LLMInvocationMetadata(
            model_identifier=model_identifier,
            model_version=model_version,
            prompt_template_hash=hashlib.sha256(prompt_text.encode()).hexdigest(),
            token_count_input=token_input,
            token_count_output=token_output,
            temperature=temperature,
            response_latency_ms=elapsed_ms,
            invocation_timestamp=invocation_timestamp,
        )

        return generated_text, metadata

    async def generate_structured(
        self,
        model_identifier: str,
        prompt_text: str,
        response_schema: type[BaseModel],
        temperature: float = 0.0,
    ) -> tuple[BaseModel, LLMInvocationMetadata]:
        """Generate structured output validated against a Pydantic schema.

        Instructs the model to respond in JSON matching the schema, then
        validates the response against the provided Pydantic model.

        Args:
            model_identifier: Model ID (e.g., "gpt-4").
            prompt_text: The prompt to send to the model.
            response_schema: Pydantic model class defining expected output structure.
            temperature: Sampling temperature (0.0 = deterministic).

        Returns:
            Tuple of (validated_model_instance, invocation_metadata).

        Raises:
            LLMConnectionError: When API is unreachable after retries or circuit is open.
        """
        schema_json = json.dumps(response_schema.model_json_schema())
        structured_prompt = (
            f"{prompt_text}\n\n"
            f"Respond ONLY with valid JSON matching this schema:\n{schema_json}"
        )

        generated_text, metadata = await self.generate_text(
            model_identifier=model_identifier,
            prompt_text=structured_prompt,
            temperature=temperature,
            max_tokens=4096,
        )

        validated_instance = response_schema.model_validate_json(generated_text)
        return validated_instance, metadata

    async def get_embeddings(
        self,
        model_identifier: str,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate embeddings for text inputs via OpenAI embeddings endpoint.

        Args:
            model_identifier: Embedding model ID (e.g., "text-embedding-3-small").
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (each a list of floats).

        Raises:
            LLMConnectionError: When API is unreachable after retries or circuit is open.
        """
        if not self._circuit_breaker.can_execute():
            raise LLMConnectionError(
                message=f"Circuit breaker OPEN for OpenAI service at {self._base_url}"
            )

        try:
            response_data = await self._embeddings_with_retry(
                model_identifier=model_identifier,
                texts=texts,
            )
            self._circuit_breaker.record_success()
        except (_RateLimitError, httpx.HTTPError) as exc:
            self._circuit_breaker.record_failure()
            raise LLMConnectionError(
                message=f"OpenAI embeddings call failed after retries: {exc}"
            ) from exc

        return self._extract_embeddings_from_response(response_data)

    @retry_with_backoff(
        max_retries=3,
        base_delay_seconds=2.0,
        exceptions=(_RateLimitError, httpx.HTTPError),
    )
    async def _chat_completion_with_retry(
        self,
        model_identifier: str,
        prompt_text: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Make a chat completion request with retry on rate limits.

        Args:
            model_identifier: The model to use.
            prompt_text: Prompt text for generation.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.

        Returns:
            Parsed JSON response dictionary.

        Raises:
            _RateLimitError: On HTTP 429 responses (triggers retry).
            httpx.HTTPError: On other HTTP errors.
        """
        payload = {
            "model": model_identifier,
            "messages": [{"role": "user", "content": prompt_text}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        response = await self._http_client.post(
            "/chat/completions",
            content=json.dumps(payload),
        )

        if response.status_code == 429:
            raise _RateLimitError(f"Rate limited by OpenAI API: {response.text}")

        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    @retry_with_backoff(
        max_retries=3,
        base_delay_seconds=2.0,
        exceptions=(_RateLimitError, httpx.HTTPError),
    )
    async def _embeddings_with_retry(
        self,
        model_identifier: str,
        texts: list[str],
    ) -> dict[str, Any]:
        """Make an embeddings request with retry on rate limits.

        Args:
            model_identifier: The embedding model to use.
            texts: List of texts to embed.

        Returns:
            Parsed JSON response dictionary.

        Raises:
            _RateLimitError: On HTTP 429 responses (triggers retry).
            httpx.HTTPError: On other HTTP errors.
        """
        payload = {
            "model": model_identifier,
            "input": texts,
        }

        response = await self._http_client.post(
            "/embeddings",
            content=json.dumps(payload),
        )

        if response.status_code == 429:
            raise _RateLimitError(f"Rate limited by OpenAI API: {response.text}")

        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    def _extract_text_from_response(self, response: dict[str, Any]) -> str:
        """Extract generated text from OpenAI chat completion response.

        Args:
            response: Parsed JSON response from chat completions endpoint.

        Returns:
            The generated text content.
        """
        choices = response.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        return str(message.get("content", ""))

    def _extract_token_counts(self, response: dict[str, Any]) -> tuple[int, int]:
        """Extract input/output token counts from OpenAI response.

        Args:
            response: Parsed JSON response dictionary.

        Returns:
            Tuple of (prompt_tokens, completion_tokens).
        """
        usage = response.get("usage", {})
        input_tokens = int(usage.get("prompt_tokens", 0))
        output_tokens = int(usage.get("completion_tokens", 0))
        return input_tokens, output_tokens

    def _extract_model_version(
        self, response: dict[str, Any], model_identifier: str
    ) -> str:
        """Extract model version from response or use model identifier.

        Args:
            response: Parsed JSON response dictionary.
            model_identifier: The model ID used for the request.

        Returns:
            Model version string.
        """
        return str(response.get("model", model_identifier))

    def _extract_embeddings_from_response(
        self, response: dict[str, Any]
    ) -> list[list[float]]:
        """Extract embedding vectors from OpenAI embeddings response.

        Args:
            response: Parsed JSON response from embeddings endpoint.

        Returns:
            List of embedding vectors ordered by index.
        """
        data = response.get("data", [])
        # Sort by index to ensure correct ordering
        sorted_data = sorted(data, key=lambda x: x.get("index", 0))
        return [[float(v) for v in item["embedding"]] for item in sorted_data]

    async def close(self) -> None:
        """Close the underlying HTTP client.

        Should be called when the adapter is no longer needed to release
        connection pool resources.
        """
        await self._http_client.aclose()
