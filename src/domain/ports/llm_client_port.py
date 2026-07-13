"""Port interface for LLM provider interactions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel

    from src.domain.schemas.reporting import ExplainabilitySchema


class LLMInvocationMetadata:
    """Metadata captured from an LLM invocation."""

    def __init__(
        self,
        model_identifier: str,
        token_count_input: int,
        token_count_output: int,
        latency_ms: int,
    ) -> None:
        """Initialize LLM invocation metadata.

        Args:
            model_identifier: The model used for generation.
            token_count_input: Number of input tokens consumed.
            token_count_output: Number of output tokens generated.
            latency_ms: Response latency in milliseconds.
        """
        self.model_identifier = model_identifier
        self.token_count_input = token_count_input
        self.token_count_output = token_count_output
        self.latency_ms = latency_ms


class LLMClientPort(ABC):
    """Abstract interface for LLM provider interactions.

    Supports text generation, structured output, and embeddings
    across multiple providers (Bedrock, OpenAI).
    """

    @abstractmethod
    async def generate_text(
        self,
        model_identifier: str,
        prompt_text: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> tuple[str, LLMInvocationMetadata]:
        """Generate text completion with metadata.

        Args:
            model_identifier: Model to use for generation.
            prompt_text: The prompt to send to the model.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            Tuple of (generated_text, invocation_metadata).
        """
        ...

    @abstractmethod
    async def generate_structured(
        self,
        model_identifier: str,
        prompt_text: str,
        response_schema: type[BaseModel],
        temperature: float = 0.0,
    ) -> tuple[BaseModel, LLMInvocationMetadata]:
        """Generate structured output validated against a Pydantic schema.

        Args:
            model_identifier: Model to use for generation.
            prompt_text: The prompt to send to the model.
            response_schema: Pydantic model class for response validation.
            temperature: Sampling temperature.

        Returns:
            Tuple of (validated_model_instance, invocation_metadata).
        """
        ...

    @abstractmethod
    async def get_embeddings(
        self, model_identifier: str, texts: list[str]
    ) -> list[list[float]]:
        """Generate embeddings for text inputs.

        Args:
            model_identifier: Embedding model to use.
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.
        """
        ...
