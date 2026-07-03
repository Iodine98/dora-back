from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock
from langchain.schema.document import Document

import pytest

from chatdoc.doc_loader.document_loader import DocumentLoader
from chatdoc.doc_loader.document_loader_factory import DocumentLoaderFactory, BaseLoader


@pytest.fixture(name="mock_document")
def fixture_mock_document():
    """
    Creates and returns a mock document object.

    Returns:
        MagicMock: A mock object with the Document specification.
    """
    mock_document = MagicMock(spec=Document)
    return mock_document


@pytest.fixture(name="mock_loader_factory")
def fixture_mock_loader_factory(mock_document):
    """
    Returns a mock loader factory object that creates a mock document loader.

    The mock document loader's `lazy_load` method returns a fresh iterator
    over `mock_document` on every call, mirroring how `DocumentLoader.map_document_iterators`
    calls `lazy_load()` once per registered file.

    Args:
        mock_document: The mock document to be yielded by each loader's iterator.

    Returns:
        MagicMock: A mock loader factory object.
    """
    mock_loader_factory = MagicMock(spec=DocumentLoaderFactory)
    mock_doc_loader = MagicMock(spec=BaseLoader)
    mock_doc_loader.lazy_load.side_effect = lambda: iter([mock_document])
    mock_loader_factory.create.return_value = mock_doc_loader
    return mock_loader_factory


@pytest.fixture(name="document_dict")
def fixture_document_dict():
    """
    Returns the dictionary of document names to paths used to build the DocumentLoader.

    Returns:
        dict[str, Path]: A dictionary containing document names as keys and file paths as values.
    """
    return {
        "doc1": Path("/path/to/doc1.docx"),
        "doc2": Path("/path/to/doc2.pdf"),
    }


@pytest.fixture(name="document_loader")
def fixture_document_loader(document_dict, mock_loader_factory):
    """
    Fixture function that creates a DocumentLoader instance with a dictionary of document paths.

    Args:
        document_dict: A dictionary containing document names as keys and file paths as values.
        mock_loader_factory: A mock loader factory object.

    Returns:
        A DocumentLoader instance.

    """
    document_loader = DocumentLoader(document_dict, mock_loader_factory)
    return document_loader


def test_document_iterators_dict_keys(document_loader, document_dict):
    """
    Test that `document_iterators_dict` is a dict keyed by the same file names
    that were passed into the DocumentLoader.
    """
    assert isinstance(document_loader.document_iterators_dict, dict)
    assert set(document_loader.document_iterators_dict.keys()) == set(document_dict.keys())


def test_document_iterators_dict_values_are_document_iterators(document_loader, mock_document):
    """
    Test that each value in `document_iterators_dict` is an iterator that yields
    `Document` instances, matching how callers (e.g. `save_files_to_vector_db` in
    `server_modules/methods.py`) consume `document_loader.document_iterators_dict[filename]`.
    """
    for file_name in document_loader.document_iterators_dict:
        document_iterator = document_loader.document_iterators_dict[file_name]
        assert isinstance(document_iterator, Iterator)
        document = next(document_iterator)
        assert isinstance(document, Document), "Should yield an instance of Document"
        assert document is mock_document
