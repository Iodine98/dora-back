import pytest
from langchain.embeddings.openai import OpenAIEmbeddings

from chatdoc.embed.embedding_factory import EmbeddingFactory


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
