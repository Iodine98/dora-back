import logging
from unittest.mock import MagicMock

import pytest

from server_modules.methods import DocumentMethods


@pytest.fixture(name="logger")
def logger_fixture() -> logging.Logger:
    """
    A logger instance to be passed into DocumentMethods calls.
    """
    return logging.getLogger("test-document-methods")


@pytest.fixture(autouse=True)
def env_fixture(monkeypatch):
    """
    Ensure the connection string environment variable used by DocumentMethods is set.
    """
    monkeypatch.setenv(
        "FINAL_ANSWER_CONNECTION_STRING", "sqlite+pysqlite:///:memory:"
    )


@pytest.fixture(name="mock_connection")
def mock_connection_fixture(monkeypatch):
    """
    Mock sqlalchemy.create_engine so no real DB connection is made, and capture the
    executed statements/values via the mocked connection.
    """
    mock_connection = MagicMock()
    mock_connection.__enter__.return_value = mock_connection
    mock_connection.__exit__.return_value = False
    mock_connection.execute.return_value = []

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_connection

    mock_create_engine = MagicMock(return_value=mock_engine)
    monkeypatch.setattr(
        "server_modules.methods.sqlalchemy.create_engine", mock_create_engine
    )
    monkeypatch.setattr(
        "server_modules.methods.DocumentModel.metadata.create_all", MagicMock()
    )
    return mock_connection


def test_add_document_ids_inserts_all_ids(mock_connection, logger):
    """
    Storing document IDs should execute a single insert statement and commit.
    """
    DocumentMethods.add_document_ids(
        session_id="session-1",
        filename="file.pdf",
        document_ids=["doc-1", "doc-2"],
        logger=logger,
    )
    assert mock_connection.execute.call_count == 1
    assert mock_connection.commit.call_count == 1


def test_add_document_ids_skips_empty_list(mock_connection, logger):
    """
    Storing an empty list of document IDs should not execute any insert statement.
    """
    DocumentMethods.add_document_ids(
        session_id="session-1", filename="file.pdf", document_ids=[], logger=logger
    )
    assert mock_connection.execute.call_count == 0


def test_get_document_ids_returns_stored_ids(mock_connection, logger):
    """
    Retrieving document IDs should return the values yielded by the executed query.
    """
    mock_connection.execute.return_value = [("doc-1",), ("doc-2",)]
    document_ids = DocumentMethods.get_document_ids(
        session_id="session-1", filename="file.pdf", logger=logger
    )
    assert document_ids == ["doc-1", "doc-2"]


def test_get_document_ids_returns_empty_list_when_none_found(mock_connection, logger):
    """
    Retrieving document IDs for an unknown session/filename should return an empty list.
    """
    mock_connection.execute.return_value = []
    document_ids = DocumentMethods.get_document_ids(
        session_id="unknown-session", filename="file.pdf", logger=logger
    )
    assert document_ids == []


def test_delete_document_ids_executes_delete_and_commits(mock_connection, logger):
    """
    Deleting document IDs should execute a delete statement and commit.
    """
    DocumentMethods.delete_document_ids(
        session_id="session-1", filename="file.pdf", logger=logger
    )
    assert mock_connection.execute.call_count == 1
    assert mock_connection.commit.call_count == 1
