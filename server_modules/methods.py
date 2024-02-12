import os
from pathlib import Path
import tempfile
import shutil
from tqdm.auto import tqdm

from flask import Flask
from werkzeug.datastructures import FileStorage

from chatdoc.doc_loader.document_loader import DocumentLoader
from chatdoc.doc_loader.document_loader_factory import DocumentLoaderFactory
from chatdoc.vector_db import VectorDatabase
from chatdoc.embed.embedding_factory import EmbeddingFactory
from chatdoc.utils import Utils

def create_tmp_dir(session_id: str) -> Path:
    """
    Create a temporary directory to store the files of the session ID in before processing them asynchronously
    Return: a Path object with the path to the new directory
    """
    if(session_id == ""):
        raise ValueError("Session ID cannot be empty")
    dir_path: Path = Path(tempfile.gettempdir()) / Path(session_id)
    os.makedirs(dir_path, exist_ok=True)
    return dir_path

def delete_tmp_dir(session_id: str) -> bool:
    """
    Delete the temporary directory coupled with the session ID when processing has finished
    Return: a bool to indicate if it succeeded
    """
    if(session_id == ""):
        raise ValueError("Session ID cannot be empty")
    dir_path: Path = Path(tempfile.gettempdir()) / Path(session_id)
    try:
        shutil.rmtree(dir_path, ignore_errors=True)
        return True
    except FileNotFoundError:
        return False



class ServerMethods:
    """
    Class representing server methods for file processing and document handling.
    """

    def __init__(self, app: Flask):
        self.app = app

    FileToPathMapping = dict[str, Path]
    OriginalFileMapping = dict[str, str]

    async def save_files_to_tmp(
        self, files: dict[str, FileStorage], session_id: str
    ) -> tuple[OriginalFileMapping, FileToPathMapping]:
        """
        Save the files to a temporary directory.

        Args:
            files (dict[str, FileStorage]): A dictionary containing the files to be saved.
            session_id (str): The ID of the session.

        Returns:
            A tuple containing the original file names and the full file paths.
        """
        dir_path = create_tmp_dir(session_id=session_id)
        self.app.logger.info(f"Created temporary directory for session {session_id}")
        original_name_dict: dict[str, str] = {}
        full_document_dict: dict[str, Path] = {}
        for filename, file in tqdm(files.items(), desc="Saving files"):
            unique_file_name = Utils.get_unique_filename(filename)
            original_name_dict[unique_file_name] = filename
            unique_file_path = dir_path / Path(unique_file_name)
            full_document_dict[unique_file_name] = unique_file_path
            file.save(unique_file_path)
        return original_name_dict, full_document_dict

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
        if delete_tmp_dir(user_id):
            self.app.logger.info(f"Cleaned up temporary directory for session {user_id}")
        else:
            self.app.logger.error(f"Failed to clean up temporary directory for session {user_id}")       
        return file_id_mapping

    async def delete_docs_from_vector_db(self, document_ids: list[str], session_id: str) -> bool:
        """
        Delete the file with the given name from the temporary directory.

        Args:
            document_ids (list[str]): A list of document IDs to be deleted.
            session_id (str): The ID of the session.

        Returns:
            None
        """
        embedding_fn = EmbeddingFactory().create()
        vector_db = VectorDatabase(session_id, embedding_fn)
        deletion_successful = await vector_db.delete_documents(document_ids)
        return deletion_successful
