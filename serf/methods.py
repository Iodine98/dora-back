import os
from pathlib import Path
import tempfile
from logging import INFO
from tqdm.auto import tqdm

from flask import Flask
from werkzeug.datastructures import FileStorage

from chatdoc.doc_loader.document_loader import DocumentLoader
from chatdoc.doc_loader.document_loader_factory import DocumentLoaderFactory
from chatdoc.vector_db import VectorDatabase
from chatdoc.embed.embedding_factory import EmbeddingFactory
from chatdoc.utils import Utils

class ServerMethods:
    """
    Class representing server methods for file processing and document handling.
    """

    def __init__(self, app: Flask):
        self.app = app

    def save_files(self, files: dict[str, FileStorage], session_id: str) -> dict[str, Path]:
        """
        Save the files to a temporary directory.

        Args:
            files (dict[str, FileStorage]): A dictionary containing the files to be saved.
            session_id (str): The ID of the session.

        Returns:
            dict[str, Path]: A dictionary mapping the unique filenames to their corresponding file paths.
        """
        dir_path: Path = Path(tempfile.gettempdir()) / Path(session_id)
        os.makedirs(dir_path, exist_ok=True)
        full_document_dict: dict[str, Path] = {}
        for filename, file in tqdm(files.items(), desc="Saving files"):
            unique_file_name = Utils.get_unique_filename(filename)
            unique_file_path = dir_path / Path(unique_file_name)
            full_document_dict[unique_file_name] = unique_file_path
            file.save(unique_file_path)
        return full_document_dict

    async def process_files(self, document_dict: dict[str, Path], user_id: str) -> None:
        """
        Process the files in the given document dictionary and add them to the vector database.

        Args:
            document_dict (dict[str, Path]): A dictionary mapping document names to their file paths.
            user_id (str): The ID of the user.

        Returns:
            None
        """
        embedding_fn = EmbeddingFactory().create()
        vector_db = VectorDatabase(user_id, embedding_fn)
        loader_factory = DocumentLoaderFactory()
        document_loader = DocumentLoader(document_dict, loader_factory, self.app.logger)
        documents = document_loader.text_splitter.split_documents(document_loader.document_iterator)
        self.app.logger.log(level=INFO, msg="Adding documents to vector database...")
        await vector_db.add_documents(documents)
