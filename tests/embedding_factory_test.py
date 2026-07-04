import httpx
import pytest
from langchain.embeddings.openai import OpenAIEmbeddings

from chatdoc.embed.embedding_factory import EmbeddingFactory
from chatdoc.http_client import HttpClientFactory


def test_env_fn_called_missing_vendor_name(monkeypatch):
    """
    Test case to ensure that a ValueError is raised when the vendor name is not
    provided and the EMBEDDING_MODEL_VENDOR_NAME environment variable is not set.
    """
    monkeypatch.delenv("EMBEDDING_MODEL_VENDOR_NAME", raising=False)
    with pytest.raises(ValueError, match="not set in environment"):
        EmbeddingFactory(embedding_model_name="gpt-3.5-turbo")


def test_env_fn_called_missing_model_name(monkeypatch):
    """
    Test case to ensure that a ValueError is raised when the model name is not
    provided and the EMBEDDING_MODEL_NAME environment variable is not set.
    """
    monkeypatch.delenv("EMBEDDING_MODEL_NAME", raising=False)
    with pytest.raises(ValueError, match="not set in environment"):
        EmbeddingFactory(vendor_name="openai")


def test_api_key_missing(monkeypatch):
    """
    Test case to ensure that an error is raised when the API key is missing.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    embedding_factory = EmbeddingFactory(vendor_name="openai", embedding_model_name="gpt-3")
    with pytest.raises(ValueError, match="not set in environment"):
        embedding_factory.create()


def test_api_key_present(monkeypatch):
    """
    Test case to ensure that the embedding is created successfully when the API
    key is provided via the OPENAI_API_KEY environment variable (set explicitly
    by this test, not by the CI environment).
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    embedding_factory = EmbeddingFactory(vendor_name="openai", embedding_model_name="gpt-3")
    assert isinstance(embedding_factory.create(), OpenAIEmbeddings)


def test_unknown_vendor_name():
    """
    Test case to ensure that an error is raised when the vendor name is unknown.
    """
    with pytest.raises(ValueError, match="No embedding available for vendor name"):
        EmbeddingFactory(vendor_name="unknown", embedding_model_name="gpt-3").create()


def test_default_http_client_is_shared_client(monkeypatch):
    """
    Test case to ensure that, when no HTTP client is injected, the
    `EmbeddingFactory` falls back to the process-wide shared client from
    `HttpClientFactory`.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    embedding_factory = EmbeddingFactory(vendor_name="openai", embedding_model_name="gpt-3")
    assert embedding_factory.http_client is HttpClientFactory.get_shared_client()
    assert embedding_factory.http_async_client is HttpClientFactory.get_shared_async_client()


def test_injected_http_client_is_used(monkeypatch):
    """
    Test case to ensure that an explicitly injected HTTP client is stored and
    used (instead of the shared client) to build the underlying OpenAI
    clients that back the `OpenAIEmbeddings` instance.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    custom_client = httpx.Client()
    custom_async_client = httpx.AsyncClient()
    try:
        embedding_factory = EmbeddingFactory(
            vendor_name="openai",
            embedding_model_name="gpt-3",
            http_client=custom_client,
            http_async_client=custom_async_client,
        )
        assert embedding_factory.http_client is custom_client
        assert embedding_factory.http_async_client is custom_async_client
        embeddings = embedding_factory.create()
        assert isinstance(embeddings, OpenAIEmbeddings)
        # `OpenAIEmbeddings.client`/`.async_client` are the `.embeddings`
        # resource of the `openai.OpenAI`/`openai.AsyncOpenAI` instances we
        # built with our injected HTTP clients.
        assert embeddings.client._client._client is custom_client
        assert embeddings.async_client._client._client is custom_async_client
    finally:
        custom_client.close()
