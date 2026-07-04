import logging
from pathlib import Path

import pytest

from server_modules.methods import DocumentMethods


@pytest.fixture(name="logger")
def logger_fixture() -> logging.Logger:
    """
    A logger instance to be passed into DocumentMethods calls.
    """
    return logging.getLogger("test-document-methods")


@pytest.fixture(autouse=True)
def env_fixture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Point FINAL_ANSWER_CONNECTION_STRING at a fresh temp-file sqlite DB per test.
    """
    db_path = tmp_path / "final_answer.db"
    monkeypatch.setenv("FINAL_ANSWER_CONNECTION_STRING", f"sqlite:///{db_path}")


def test_add_document_ids_inserts_all_ids(logger: logging.Logger) -> None:
    """
    Storing document IDs should persist all of them for the session/filename.
    """
    DocumentMethods.add_document_ids(
        session_id="session-1",
        filename="file.pdf",
        document_ids=["doc-1", "doc-2"],
        logger=logger,
    )
    document_ids = DocumentMethods.get_document_ids(
        session_id="session-1", filename="file.pdf", logger=logger
    )
    assert sorted(document_ids) == ["doc-1", "doc-2"]


def test_add_document_ids_skips_empty_list(logger: logging.Logger) -> None:
    """
    Storing an empty list of document IDs should not persist anything.
    """
    DocumentMethods.add_document_ids(
        session_id="session-1", filename="file.pdf", document_ids=[], logger=logger
    )
    document_ids = DocumentMethods.get_document_ids(
        session_id="session-1", filename="file.pdf", logger=logger
    )
    assert document_ids == []


def test_get_document_ids_returns_empty_list_when_none_found(
    logger: logging.Logger,
) -> None:
    """
    Retrieving document IDs for an unknown session/filename should return an empty list.
    """
    document_ids = DocumentMethods.get_document_ids(
        session_id="unknown-session", filename="file.pdf", logger=logger
    )
    assert document_ids == []


def test_delete_document_ids_removes_stored_ids(logger: logging.Logger) -> None:
    """
    Deleting document IDs should remove all stored ids for the session/filename.
    """
    DocumentMethods.add_document_ids(
        session_id="session-1",
        filename="file.pdf",
        document_ids=["doc-1", "doc-2"],
        logger=logger,
    )
    DocumentMethods.delete_document_ids(
        session_id="session-1", filename="file.pdf", logger=logger
    )
    document_ids = DocumentMethods.get_document_ids(
        session_id="session-1", filename="file.pdf", logger=logger
    )
    assert document_ids == []
