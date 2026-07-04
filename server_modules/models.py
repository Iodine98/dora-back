import json
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ChatHistoryBase(DeclarativeBase):
    """
    Declarative base for models that live in the chat-history database.

    Kept separate from :class:`FinalAnswerBase` so that ``metadata.create_all``
    only creates the tables that belong to their respective database/engine.
    """


class FinalAnswerBase(DeclarativeBase):
    """
    Declarative base for models that live in the final-answer database.

    Kept separate from :class:`ChatHistoryBase` so that ``metadata.create_all``
    only creates the tables that belong to their respective database/engine.
    """


class ChatHistoryModel(ChatHistoryBase):
    __tablename__ = "message_store"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36))
    message: Mapped[dict[str, Any]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())


class DocumentModel(FinalAnswerBase):
    """
    Tracks the document IDs that were produced when a file was ingested into the
    vector database, scoped to the session (user) that uploaded it. This allows the
    delete endpoint to look up which document IDs belong to a given file/session
    instead of requiring the client to supply them in the request payload.
    """

    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    document_id: Mapped[str] = mapped_column(String(255))

    def __repr__(self) -> str:
        return f"Document(session_id={self.session_id}, filename={self.filename}, document_id={self.document_id})"


class FinalAnswerModel(FinalAnswerBase):
    __tablename__ = "final_answer"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    start_time: Mapped[datetime | None] = mapped_column(default=None)
    end_time: Mapped[datetime | None] = mapped_column(default=None)
    number_of_messages: Mapped[int] = mapped_column(default=-1)
    original_answer: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    edited_answer: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)

    def __repr__(self) -> str:
        return (
            f"FinalAnswer(session_id={self.session_id}, "
            f"original_answer={json.dumps(self.original_answer)}, "
            f"edited_answer={json.dumps(self.edited_answer)}, "
            f"start_time={self.start_time}, end_time={self.end_time})"
        )
