"""Unit tests for LLM adapters (Bedrock and OpenAI)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from botocore.exceptions import ClientError

from src.domain.exceptions import LLMConnectionError
from src.domain.schemas.audit import LLMInvocationMetadata
from src.infrastructure.adapters.bedrock_adapter import BedrockAdapter
from src.infrastructure.adapters.openai_adapter import OpenAIAdapter


# ============================================================================
# BedrockAdapter Tests
# ============================================================================


class TestBedrockAdapterGenerateText:
    """Tests for BedrockAdapter.generate_text method."""

    @pytest.fixture()
    def adapter(self) -> BedrockAdapter:
        """Create a BedrockAdapter with mocked boto3 client."""
        with patch("src.infrastructure.adapters.bedrock_adapter.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            adapter = BedrockAdapter(region="us-east-1")
            adapter._client = mock_client
            return adapter

    @pytest.mark.asyncio()
    async def test_generate_text_returns_text_and_metadata(
        self, adapter: BedrockAdapter
    ) -> None:
        """Verify generate_text returns generated text and metadata tuple."""
        response_body = {
            "content": [{"type": "text", "text": "Hello, world!"}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
            "model": "anthropic.claude-3-sonnet-20240229-v1:0",
        }
        mock_response = MagicMock()
        mock_response.__getitem__ = lambda self, key: (
            {"body": MagicMock(read=MagicMock(return_value=json.dumps(response_body).encode()))}[
                key
            ]
        )
        adapter._client.invoke_model.return_value = {
            "body": MagicMock(read=MagicMock(return_value=json.dumps(response_body).encode()))
        }

        text, metadata = await adapter.generate_text(
            model_identifier="anthropic.claude-3-sonnet-20240229-v1:0",
            prompt_text="Say hello",
            temperature=0.0,
            max_tokens=100,
        )

        assert text == "Hello, world!"
        assert isinstance(metadata, LLMInvocationMetadata)
        assert metadata.model_identifier == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert metadata.token_count_input == 10
        assert metadata.token_count_output == 5
        assert metadata.temperature == 0.0

    @pytest.mark.asyncio()
    async def test_generate_text_raises_on_circuit_open(
        self, adapter: BedrockAdapter
    ) -> None:
        """Verify LLMConnectionError when circuit breaker is open."""
        # Force circuit open
        for _ in range(5):
            adapter._circuit_breaker.record_failure()

        with pytest.raises(LLMConnectionError, match="Circuit breaker OPEN"):
            await adapter.generate_text(
                model_identifier="anthropic.claude-3-sonnet",
                prompt_text="test",
            )

    @pytest.mark.asyncio()
    async def test_generate_text_raises_after_retries_exhausted(
        self, adapter: BedrockAdapter
    ) -> None:
        """Verify LLMConnectionError is raised after retries are exhausted."""
        error_response = {"Error": {"Code": "ServiceUnavailableException", "Message": "Unavailable"}}
        adapter._client.invoke_model.side_effect = ClientError(error_response, "InvokeModel")

        with pytest.raises(LLMConnectionError, match="failed after retries"):
            await adapter.generate_text(
                model_identifier="anthropic.claude-3-sonnet",
                prompt_text="test",
            )


class TestBedrockAdapterGetEmbeddings:
    """Tests for BedrockAdapter.get_embeddings method."""

    @pytest.fixture()
    def adapter(self) -> BedrockAdapter:
        """Create a BedrockAdapter with mocked boto3 client."""
        with patch("src.infrastructure.adapters.bedrock_adapter.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            adapter = BedrockAdapter(region="us-east-1")
            adapter._client = mock_client
            return adapter

    @pytest.mark.asyncio()
    async def test_get_embeddings_returns_vectors(self, adapter: BedrockAdapter) -> None:
        """Verify get_embeddings returns list of float vectors."""
        response_body = {"embedding": [0.1, 0.2, 0.3]}
        adapter._client.invoke_model.return_value = {
            "body": MagicMock(read=MagicMock(return_value=json.dumps(response_body).encode()))
        }

        embeddings = await adapter.get_embeddings(
            model_identifier="amazon.titan-embed-text-v2:0",
            texts=["test text"],
        )

        assert len(embeddings) == 1
        assert embeddings[0] == [0.1, 0.2, 0.3]


# ============================================================================
# OpenAIAdapter Tests
# ============================================================================


class TestOpenAIAdapterGenerateText:
    """Tests for OpenAIAdapter.generate_text method."""

    @pytest.fixture()
    def adapter(self) -> OpenAIAdapter:
        """Create an OpenAIAdapter instance."""
        return OpenAIAdapter(api_key="test-key", base_url="https://api.test.com/v1")

    @pytest.mark.asyncio()
    async def test_generate_text_returns_text_and_metadata(
        self, adapter: OpenAIAdapter
    ) -> None:
        """Verify generate_text returns generated text and metadata."""
        mock_response_data = {
            "choices": [{"message": {"content": "Generated response"}}],
            "usage": {"prompt_tokens": 15, "completion_tokens": 8},
            "model": "gpt-4-0613",
        }
        mock_response = httpx.Response(
            status_code=200,
            json=mock_response_data,
            request=httpx.Request("POST", "https://api.test.com/v1/chat/completions"),
        )

        with patch.object(adapter._http_client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            text, metadata = await adapter.generate_text(
                model_identifier="gpt-4",
                prompt_text="Tell me something",
                temperature=0.5,
                max_tokens=200,
            )

        assert text == "Generated response"
        assert isinstance(metadata, LLMInvocationMetadata)
        assert metadata.model_identifier == "gpt-4"
        assert metadata.model_version == "gpt-4-0613"
        assert metadata.token_count_input == 15
        assert metadata.token_count_output == 8
        assert metadata.temperature == 0.5

    @pytest.mark.asyncio()
    async def test_generate_text_raises_on_circuit_open(
        self, adapter: OpenAIAdapter
    ) -> None:
        """Verify LLMConnectionError when circuit breaker is open."""
        for _ in range(5):
            adapter._circuit_breaker.record_failure()

        with pytest.raises(LLMConnectionError, match="Circuit breaker OPEN"):
            await adapter.generate_text(
                model_identifier="gpt-4",
                prompt_text="test",
            )

    @pytest.mark.asyncio()
    async def test_generate_text_raises_after_rate_limit_retries(
        self, adapter: OpenAIAdapter
    ) -> None:
        """Verify LLMConnectionError after rate limit retries exhausted."""
        mock_response = httpx.Response(
            status_code=429,
            text="Rate limit exceeded",
            request=httpx.Request("POST", "https://api.test.com/v1/chat/completions"),
        )

        with patch.object(adapter._http_client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            with pytest.raises(LLMConnectionError, match="failed after retries"):
                await adapter.generate_text(
                    model_identifier="gpt-4",
                    prompt_text="test",
                )


class TestOpenAIAdapterGetEmbeddings:
    """Tests for OpenAIAdapter.get_embeddings method."""

    @pytest.fixture()
    def adapter(self) -> OpenAIAdapter:
        """Create an OpenAIAdapter instance."""
        return OpenAIAdapter(api_key="test-key", base_url="https://api.test.com/v1")

    @pytest.mark.asyncio()
    async def test_get_embeddings_returns_vectors(self, adapter: OpenAIAdapter) -> None:
        """Verify get_embeddings returns correctly ordered embedding vectors."""
        mock_response_data = {
            "data": [
                {"index": 1, "embedding": [0.4, 0.5, 0.6]},
                {"index": 0, "embedding": [0.1, 0.2, 0.3]},
            ]
        }
        mock_response = httpx.Response(
            status_code=200,
            json=mock_response_data,
            request=httpx.Request("POST", "https://api.test.com/v1/embeddings"),
        )

        with patch.object(adapter._http_client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            embeddings = await adapter.get_embeddings(
                model_identifier="text-embedding-3-small",
                texts=["first", "second"],
            )

        assert len(embeddings) == 2
        # Should be sorted by index
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [0.4, 0.5, 0.6]


class TestOpenAIAdapterGenerateStructured:
    """Tests for OpenAIAdapter.generate_structured method."""

    @pytest.fixture()
    def adapter(self) -> OpenAIAdapter:
        """Create an OpenAIAdapter instance."""
        return OpenAIAdapter(api_key="test-key", base_url="https://api.test.com/v1")

    @pytest.mark.asyncio()
    async def test_generate_structured_validates_response(
        self, adapter: OpenAIAdapter
    ) -> None:
        """Verify generate_structured parses and validates JSON against schema."""
        from pydantic import BaseModel

        class SimpleResponse(BaseModel):
            name: str
            score: float

        json_output = '{"name": "test", "score": 0.95}'
        mock_response_data = {
            "choices": [{"message": {"content": json_output}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10},
            "model": "gpt-4",
        }
        mock_response = httpx.Response(
            status_code=200,
            json=mock_response_data,
            request=httpx.Request("POST", "https://api.test.com/v1/chat/completions"),
        )

        with patch.object(adapter._http_client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result, metadata = await adapter.generate_structured(
                model_identifier="gpt-4",
                prompt_text="Generate a response",
                response_schema=SimpleResponse,
            )

        assert isinstance(result, SimpleResponse)
        assert result.name == "test"
        assert result.score == 0.95
        assert isinstance(metadata, LLMInvocationMetadata)
