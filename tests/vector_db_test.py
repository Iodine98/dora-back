from unittest.mock import patch, MagicMock

import pytest
from langchain_core.vectorstores import VectorStore

from chatdoc.vector_db import VectorDatabase


@pytest.fixture(name="mock_embedding_fn")
def mock_embedding_fn_fixture():
    """
    Returns a mock embedding function to be used when instantiating a
    `VectorDatabase` without hitting a real embedding model.
    """
    return MagicMock()


@patch("chatdoc.vector_db.Chroma")
@patch("chatdoc.vector_db.PersistentClient")
def test_chroma_client_dev_uses_persistent_client(
    mock_persistent_client, mock_chroma, mock_embedding_fn, monkeypatch
):
    """
    In `DEV`/`TST` environments the vector database should use a local
    `PersistentClient` rather than connecting to a remote Chroma server.
    """
    monkeypatch.setenv("CURRENT_ENV", "DEV")
    mock_persistent_client.return_value = MagicMock()
    mock_chroma.return_value = MagicMock(spec=VectorStore)

    vector_db = VectorDatabase(collection_name="test", embedding_fn=mock_embedding_fn)

    assert vector_db.chroma_client is mock_persistent_client.return_value
    mock_persistent_client.assert_called_once()


@patch("chatdoc.vector_db.Chroma")
@patch("chatdoc.vector_db.HttpClient")
def test_chroma_client_prod_uses_http_client(
    mock_http_client, mock_chroma, mock_embedding_fn, monkeypatch
):
    """
    In `PROD`, the vector database should connect to the Chroma server (e.g.
    the `dora-chromadb` docker-compose service) over HTTP using
    `CHROMA_SERVER_HOST`/`CHROMA_SERVER_PORT`.
    """
    monkeypatch.setenv("CURRENT_ENV", "PROD")
    monkeypatch.setenv("CHROMA_SERVER_HOST", "some-chroma-host")
    monkeypatch.setenv("CHROMA_SERVER_PORT", "1234")
    mock_http_client.return_value = MagicMock()
    mock_chroma.return_value = MagicMock(spec=VectorStore)

    vector_db = VectorDatabase(collection_name="test", embedding_fn=mock_embedding_fn)

    assert vector_db.chroma_client is mock_http_client.return_value
    mock_http_client.assert_called_once_with(host="some-chroma-host", port=1234)


@patch("chatdoc.vector_db.Chroma")
@patch("chatdoc.vector_db.HttpClient")
def test_chroma_client_prod_uses_default_host_and_port(
    mock_http_client, mock_chroma, mock_embedding_fn, monkeypatch
):
    """
    When `CHROMA_SERVER_HOST`/`CHROMA_SERVER_PORT` are not set, sensible
    defaults matching the `dora-chromadb` docker-compose service should be
    used.
    """
    monkeypatch.setenv("CURRENT_ENV", "PROD")
    monkeypatch.delenv("CHROMA_SERVER_HOST", raising=False)
    monkeypatch.delenv("CHROMA_SERVER_PORT", raising=False)
    mock_http_client.return_value = MagicMock()
    mock_chroma.return_value = MagicMock(spec=VectorStore)

    vector_db = VectorDatabase(collection_name="test", embedding_fn=mock_embedding_fn)

    assert vector_db.chroma_client is mock_http_client.return_value
    mock_http_client.assert_called_once_with(host="dora-chromadb", port=8000)


def test_chroma_client_invalid_env_raises(mock_embedding_fn, monkeypatch):
    """
    An invalid `CURRENT_ENV` value should raise a `ValueError`.
    """
    monkeypatch.setenv("CURRENT_ENV", "INVALID")
    with pytest.raises(ValueError):
        VectorDatabase(collection_name="test", embedding_fn=mock_embedding_fn)
