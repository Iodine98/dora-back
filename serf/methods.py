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

    async def save_files_to_tmp(self, files: dict[str, FileStorage], session_id: str) -> dict[str, Path]:
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

    async def save_files_to_vector_db(self, file_dict: dict[str, Path], user_id: str) -> dict[str, list[str]]:
        """
        Process the files in the given document dictionary and add them to the vector database.

        Args:
            document_dict (dict[str, Path]): A dictionary mapping document names to their file paths.
            user_id (str): The ID of the user.

        Returns:
            A dictionary of file names and their corresponding document IDs.
        """
        embedding_fn = EmbeddingFactory().create()
        vector_db = VectorDatabase(user_id, embedding_fn)
        loader_factory = DocumentLoaderFactory()
        document_loader = DocumentLoader(file_dict, loader_factory, self.app.logger)
        file_id_mapping = {}
        for filename in tqdm(file_dict.keys(), desc="Processing files"):
            document_iterator = document_loader.document_iterators_dict[filename]
            documents = document_loader.text_splitter.split_documents(document_iterator)
            document_ids = await vector_db.add_documents(documents)
            file_id_mapping[filename] = document_ids
        return file_id_mapping

    async def delete_file_from_vector_db(self, file_name: str, session_id: str) -> bool:
        """
        Delete the file with the given name from the temporary directory.

        Args:
            file_name (str): The name of the file to be deleted.
            session_id (str): The ID of the session.

        Returns:
            None
        """
        embedding_fn = EmbeddingFactory().create()
        vector_db = VectorDatabase(session_id, embedding_fn)
        deletion_successful = await vector_db.delete_document(file_name)
        return deletion_successful
