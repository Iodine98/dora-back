from pathlib import Path
from logging import Logger
from typing import Iterator
from tqdm.auto import tqdm
import os

from langchain.text_splitter import RecursiveCharacterTextSplitter, TextSplitter
from langchain.schema import Document

from chatdoc.doc_loader.document_loader_factory import DocumentLoaderFactory, BaseLoader


class DocumentLoader:
    """
    A class that loads documents using a loader factory.

    Args:
        document_dict (dict): A dictionary containing document names as keys and file paths as values.
        loader_factory (LoaderFactory): An instance of the loader factory used to create loaders.

    Attributes:
        loader_factory (LoaderFactory): The loader factory used to create loaders.
        loaders (list): A list of loaders initialized using the document dictionary.

    Methods:
        initialize_loaders: Initializes the loaders using the document dictionary.
        chain_document_iterators: Chains the document iterators from all loaders.

    """

    def __init__(
        self, document_dict: dict[str, Path], loader_factory: DocumentLoaderFactory, logger: Logger | None = None
    ):
        self.loader_factory = loader_factory
        self.logger = logger if logger else Logger("DocumentLoader")
        self.loaders_dict: dict[str, BaseLoader] = self.initialize_loaders(document_dict)
        self.document_iterators_dict: dict[str, Iterator[Document]] = self.map_document_iterators()
        self.text_splitter: TextSplitter = self.load_token_text_splitter()

    def initialize_loaders(self, document_dict: dict[str, Path]) -> dict[str, BaseLoader]:
        """
        Initializes the loaders using the document dictionary.

        Args:
            document_dict (dict): A dictionary containing document names as keys and file paths as values.

        Returns:
            list: A list of loaders initialized using the document dictionary.

        """
        loaders_dict = {
            file_name: self.loader_factory.create(
                abs_file_path=str(file_path_obj.absolute()),
                file_extension=file_path_obj.suffix,
            )
            for file_name, file_path_obj in tqdm(document_dict.items(), desc="load documents")
        }
        return loaders_dict

    def map_document_iterators(self) -> dict[str, Iterator[Document]]:
        """
        Chains the document iterators from all loaders.

        Returns:
            itertools.chain: An iterator that chains the document iterators from all loaders.

        """
        return {
            file_name: loader.lazy_load()
            for file_name, loader in tqdm(self.loaders_dict.items(), desc="map document iterators")
        }

    def load_token_text_splitter(self) -> TextSplitter:
        """
        Load and return the TextSplitter instance.

        If the chunk size is specified in the environment variable "CHUNK_SIZE",
        it will be used. Otherwise, if the chunk size is specified in the kwargs,
        it will be used. Otherwise, a default chunk size of 1000 will be used.

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            TextSplitter: An instance of TextSplitter.

        """
        if "CHUNK_SIZE" in os.environ:
            chunk_size = int(os.environ["CHUNK_SIZE"])
            self.logger.info(msg=f"Using chunk size of {chunk_size}")
        else:
            self.logger.info(msg="No chunk size specified, defaulting to 1000")
            chunk_size = 1000
        if "CHUNK_OVERLAP" in os.environ:
            chunk_overlap = int(os.environ["CHUNK_OVERLAP"])
            self.logger.info(msg=f"Using chunk overlap of {chunk_overlap} tokens")
        else:
            self.logger.info(msg="No chunk overlap specified, defaulting to 0")
            chunk_overlap = 0
        return RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
