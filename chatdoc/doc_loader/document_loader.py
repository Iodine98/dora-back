from pathlib import Path
from itertools import chain
from logging import Logger, INFO
from tqdm.auto import tqdm
import os

from langchain.text_splitter import TokenTextSplitter, TextSplitter
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
        self.loaders = self.initialize_loaders(document_dict)
        self.document_iterator = self.chain_document_iterators()
        self.text_splitter: TextSplitter = self.load_token_text_splitter()

    def initialize_loaders(self, document_dict: dict[str, Path]) -> list[BaseLoader]:
        """
        Initializes the loaders using the document dictionary.

        Args:
            document_dict (dict): A dictionary containing document names as keys and file paths as values.

        Returns:
            list: A list of loaders initialized using the document dictionary.

        """
        loaders = [
            self.loader_factory.create(
                abs_file_path=str(file_path_obj.absolute()),
                file_extension=file_path_obj.suffix,
            )
            for file_path_obj in tqdm(document_dict.values(), desc="load documents")
        ]
        return loaders

    def chain_document_iterators(self) -> chain[Document]:
        """
        Chains the document iterators from all loaders.

        Returns:
            itertools.chain: An iterator that chains the document iterators from all loaders.

        """
        return chain(*[loader.lazy_load() for loader in tqdm(self.loaders, desc="chain document iterators")])

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
            self.logger.log(level=INFO, msg=f"Using chunk size of {chunk_size}")
        else:
            self.logger.log(level=INFO, msg="No chunk size specified, defaulting to 1000")
            chunk_size = 1000
        return TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=0, disallowed_special=())
