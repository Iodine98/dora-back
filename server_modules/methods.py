import os
from pathlib import Path
import tempfile
import shutil
import logging
from datetime import datetime
from typing import Any
from tqdm.auto import tqdm

from flask import Flask
import sqlalchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.datastructures import FileStorage

from chatdoc.doc_loader.document_loader import DocumentLoader
from chatdoc.doc_loader.document_loader_factory import DocumentLoaderFactory
from chatdoc.vector_db import VectorDatabase
from chatdoc.embed.embedding_factory import EmbeddingFactory
from chatdoc.utils import Utils
from server_modules.models import FinalAnswerModel, ChatHistoryModel


def create_tmp_dir(session_id: str) -> Path:
    """
    Create a temporary directory to store the files of the session ID in before processing them asynchronously
    Return: a Path object with the path to the new directory
    """
    if session_id == "":
        raise ValueError("Session ID cannot be empty")
    dir_path: Path = Path(tempfile.gettempdir()) / Path(session_id)
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def delete_tmp_dir(session_id: str) -> bool:
    """
    Delete the temporary directory coupled with the session ID when processing has finished
    Return: a bool to indicate if it succeeded
    """
    if session_id == "":
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

    async def save_files_to_vector_db(
        self, file_dict: dict[str, Path], user_id: str
    ) -> dict[str, list[str]]:
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
            self.app.logger.info(
                f"Cleaned up temporary directory for session {user_id}"
            )
        else:
            self.app.logger.error(
                f"Failed to clean up temporary directory for session {user_id}"
            )
        return file_id_mapping

    async def delete_docs_from_vector_db(
        self, document_ids: list[str], session_id: str
    ) -> bool:
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


class ExperimentSessionMethods:
    """
    Method class for handling the creation and updating of experiment sessions.
    """

    @staticmethod
    def __parse_dates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Parse the datetime objects in the rows to strings
        """
        for row in rows:
            for column, value in row.items():
                if isinstance(value, datetime):
                    row[column] = value.strftime("%Y-%m-%d %H:%M:%S")
        return rows

    @staticmethod
    def __get_rows(
        connection_string: str, table_model: type[DeclarativeBase]
    ) -> list[dict[str, Any]]:
        """
        Get all the rows from the given table
        """
        db_engine = sqlalchemy.create_engine(connection_string)
        with db_engine.connect() as connection:
            query = sqlalchemy.select(table_model)
            result = connection.execute(query)
            rows = [dict(row._asdict()) for row in result]
            formatted_rows = ExperimentSessionMethods.__parse_dates(rows)
            return formatted_rows


    @staticmethod
    def add_new_session(session_id: str, logger: logging.Logger) -> None:
        """
        Add a new record to the final_answer table when the user starts a new session
        """
        logger.info(f"Adding new record for session id: {session_id}")
        db_engine = sqlalchemy.create_engine(
            Utils.get_env_variable("FINAL_ANSWER_CONNECTION_STRING")
        )
        FinalAnswerModel.metadata.create_all(
            db_engine
        )  # CREATE TABLE IF NOT EXISTS final_answer
        answer_model_record_query = sqlalchemy.select(FinalAnswerModel).where(
            FinalAnswerModel.session_id == session_id
        )  # SELECT * FROM final_answer WHERE session_id = session_id
        insertion_stmt = sqlalchemy.insert(FinalAnswerModel).values(
            session_id=session_id,
            start_time=sqlalchemy.func.now(),  # pylint: disable=not-callable
        )  # pylint: disable=not-callable
        update_stmt = (
            sqlalchemy.update(FinalAnswerModel)
            .where(FinalAnswerModel.session_id == session_id)
            .values(
                start_time=sqlalchemy.func.now(),  # pylint: disable=not-callable
                original_answer={},
                edited_answer={},
                end_time=None,
                number_of_messages=-1,
            )
        )  # INSERT INTO final_answer (session_id, original_answer, edited_answer) VALUES (session_id, original_answer, edited_answer)
        with db_engine.connect() as connection:
            answer_model_record = connection.execute(answer_model_record_query)
            if not answer_model_record.fetchone():
                connection.execute(insertion_stmt)
            else:
                connection.execute(update_stmt)
            connection.commit()

    @staticmethod
    def update_session(
        session_id: str,
        original_answer: dict,
        edited_answer: dict,
        logger: logging.Logger,
    ) -> None:
        """
        Update the final_answer table with the original and edited answers
        """
        db_final_answer_engine = sqlalchemy.create_engine(
            Utils.get_env_variable("FINAL_ANSWER_CONNECTION_STRING")
        )
        logger.info(f"Updating final answer for session_id: {session_id}")
        answer_model_record_query = sqlalchemy.select(FinalAnswerModel).where(
            FinalAnswerModel.session_id == session_id
        )  # SELECT * FROM final_answer WHERE session_id = session_id
        update_stmt = (
            sqlalchemy.update(FinalAnswerModel)
            .where(FinalAnswerModel.session_id == session_id)
            .values(
                original_answer=original_answer,
                edited_answer=edited_answer,
                end_time=sqlalchemy.func.now(),  # pylint: disable=not-callable
            )
        )  # UPDATE final_answer SET original_answer = original_answer, edited_answer = edited_answer, end_time = NOW() WHERE session_id = session_id
        with db_final_answer_engine.connect() as connection:
            answer_model_record = connection.execute(answer_model_record_query)
            if not answer_model_record.fetchone():
                raise ValueError(f"No record found for session_id: {session_id}")
            connection.execute(update_stmt)
            connection.commit()
        db_chat_history_engine = sqlalchemy.create_engine(
            Utils.get_env_variable("CHAT_HISTORY_CONNECTION_STRING")
        )
        count_stmt = sqlalchemy.select(
            sqlalchemy.func.count(ChatHistoryModel.id)  # pylint: disable=not-callable
        ).where(ChatHistoryModel.session_id == session_id)
        with db_chat_history_engine.connect() as connection:
            number_of_messages = connection.execute(count_stmt).scalar()
            if number_of_messages is None:
                raise ValueError(f"No chat history found for session_id: {session_id}")
        update_message_count = (
            sqlalchemy.update(FinalAnswerModel)
            .where(FinalAnswerModel.session_id == session_id)
            .values(number_of_messages=number_of_messages)
        )
        with db_final_answer_engine.connect() as connection:
            connection.execute(update_message_count)
            connection.commit()

    @staticmethod
    def retrieve_sessions(logger: logging.Logger) -> list[dict[str, Any]]:
        """
        Get all the sessions from the final_answer table
        """
        sessions = ExperimentSessionMethods.__get_rows(
            connection_string=Utils.get_env_variable("FINAL_ANSWER_CONNECTION_STRING"),
            table_model=FinalAnswerModel,
        )
        logger.info(f"Retrieved {len(sessions)} sessions from the final_answer table")
        return sessions

    @staticmethod
    def retrieve_chat_history(logger: logging.Logger) -> list[dict[str, Any]]:
        """
        Get all the chat history from the chat_history table
        """
        chat_history = ExperimentSessionMethods.__get_rows(
            connection_string=Utils.get_env_variable("CHAT_HISTORY_CONNECTION_STRING"),
            table_model=ChatHistoryModel,
        )
        logger.info(
            f"Retrieved {len(chat_history)} chat history from the chat_history table"
        )
        return chat_history
