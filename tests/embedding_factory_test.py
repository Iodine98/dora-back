import os

import pytest
from langchain.embeddings.openai import OpenAIEmbeddings

from chatdoc.embed.embedding_factory import EmbeddingFactory


def test_env_fn_called_missing_vendor_name():
    """
    Test case to ensure that the env_fn is called when the vendor name is not set.
    """
    embedding_factory = EmbeddingFactory(embedding_model_name="gpt-3.5-turbo")
    if "EMBEDDING_MODEL_VENDOR_NAME" in os.environ:
        assert embedding_factory.vendor_name == os.environ["EMBEDDING_MODEL_VENDOR_NAME"]
    else:
        with pytest.raises(ValueError, match="not set in environment"):
            embedding_factory.create()


def test_env_fn_called_missing_model_name():
    """
    Test case to ensure that the env_fn is called when the model name is not set.
    """
    embedding_factory = EmbeddingFactory(vendor_name="openai")
    if "EMBEDDING_MODEL_NAME" in os.environ:
        assert embedding_factory.embedding_model_name == os.environ["EMBEDDING_MODEL_NAME"]
    else:
        with pytest.raises(ValueError, match="not set in environment"):
            embedding_factory.create()


def test_api_key_missing():
    """
    Test case to ensure that an error is raised when the API key is missing.
    """
    embedding_factory = EmbeddingFactory(vendor_name="openai", embedding_model_name="gpt-3")
    if "OPENAI_API_KEY" in os.environ:
        assert isinstance(embedding_factory.create(), OpenAIEmbeddings)
    else:
        with pytest.raises(ValueError, match="not set in environment"):
            embedding_factory.create()


def test_unknown_vendor_name():
    """
    Test case to ensure that an error is raised when the vendor name is unknown.
    """
    with pytest.raises(ValueError, match="No embedding available for vendor name"):
        EmbeddingFactory(vendor_name="unknown", embedding_model_name="gpt-3").create()
