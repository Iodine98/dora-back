from unittest.mock import MagicMock
from collections.abc import Iterator
import pytest
from langchain.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredExcelLoader,
    UnstructuredXMLLoader,
)
from chatdoc.doc_loader.document_loader_factory import DocumentLoaderFactory


@pytest.fixture(name="loader_factory_pdf")
def loader_factory_pdf_fixture() -> Iterator[DocumentLoaderFactory]:
    """
    Fixture for testing the loader_factory function with PyPDFLoader.

    Args:
        loader_factory: The loader_factory function to be tested.

    Yields:
        LoaderFactory: The result of calling the loader_factory function.
    """
    mock_loader = MagicMock(spec=DocumentLoaderFactory)
    mock_loader.create.return_value = MagicMock(spec=PyPDFLoader)
    return mock_loader


@pytest.fixture(name="loader_factory_docx")
def loader_factory_docx_fixture() -> Iterator[DocumentLoaderFactory]:
    """
    Fixture for testing the loader_factory function with Docx2txtLoader.

    Args:
        loader_factory: The loader_factory function to be tested.

    Yields:
        LoaderFactory: The loader_factory function called with the mocked Docx2txtLoader.
    """
    mock_loader = MagicMock(spec=DocumentLoaderFactory)
    mock_loader.create.return_value = MagicMock(spec=Docx2txtLoader)
    return mock_loader


@pytest.fixture(name="loader_factory_excel")
def loader_factory_excel_fixture() -> Iterator[DocumentLoaderFactory]:
    """
    Fixture for testing the loader_factory function with UnstructuredExcelLoader.

    Args:
        loader_factory: The loader_factory function to be tested.

    Yields:
        LoaderFactory: The loader_factory function called with the mocked UnstructuredExcelLoader.
    """
    mock_loader = MagicMock(spec=DocumentLoaderFactory)
    mock_loader.create.return_value = MagicMock(spec=UnstructuredExcelLoader)
    return mock_loader


@pytest.fixture(name="loader_factory_xml")
def loader_factory_xml_fixture() -> Iterator[DocumentLoaderFactory]:
    """
    Fixture for testing the loader_factory function with UnstructuredXMLLoader.

    Args:
        loader_factory: The loader_factory function to be tested.

    Yields:
        LoaderFactory: The loader_factory function called with the mocked UnstructuredXMLLoader.
    """
    mock_loader = MagicMock(spec=DocumentLoaderFactory)
    mock_loader.create.return_value = MagicMock(spec=UnstructuredXMLLoader)
    return mock_loader


def test_create_pdf_loader(loader_factory_pdf):
    """
    Test case for creating a PDF loader.
    """
    dummy_file_path = "/dummy/path/file.pdf"
    loader = loader_factory_pdf.create(dummy_file_path, ".pdf")
    assert isinstance(loader, PyPDFLoader)


def test_create_word_loader(loader_factory_docx):
    """
    Test case for creating a PDF loader.
    """
    dummy_file_path = "/dummy/path/file.docx"
    loader = loader_factory_docx.create(dummy_file_path, ".docx")
    assert isinstance(loader, Docx2txtLoader)


def test_create_excel_loader(loader_factory_excel):
    """
    Test case for creating an Excel loader.
    """
    dummy_file_path = "/dummy/path/file.xlsx"
    loader = loader_factory_excel.create(dummy_file_path, ".xlsx")
    assert isinstance(loader, UnstructuredExcelLoader)


def test_create_xml_loader(loader_factory_xml):
    """
    Test case for creating an XML loader.
    """
    dummy_file_path = "/dummy/path/file.xml"
    loader = loader_factory_xml.create(dummy_file_path, ".xml")
    assert isinstance(loader, UnstructuredXMLLoader)
