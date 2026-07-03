from langchain.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredExcelLoader,
    UnstructuredXMLLoader,
)
from langchain.document_loaders.base import BaseLoader


class DocumentLoaderFactory:
    """
    Factory class for creating document loaders based on file extension.
    """

    def __init__(self):
        self.loader_map: dict[str, type[BaseLoader]] = {
            ".pdf": PyPDFLoader,
            ".docx": Docx2txtLoader,
            ".xlsx": UnstructuredExcelLoader,
            ".xml": UnstructuredXMLLoader,
            # Add other file types and their corresponding loaders here
        }

    def create(self, abs_file_path: str, file_extension: str) -> BaseLoader:
        """
        Create a document loader based on the file extension.

        Args:
            abs_file_path (str): The absolute file path of the document.
            file_extension (str): The file extension of the document.

        Returns:
            BaseLoader: An instance of the appropriate document loader.

        Raises:
            ValueError: If no loader is available for the given file extension.
        """
        loader_class = self.loader_map.get(file_extension)
        if loader_class is None:
            raise ValueError(f"No loader available for file extension {file_extension}")
        return loader_class(abs_file_path)
