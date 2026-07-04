import logging
from typing import List

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server_modules.models import ChatHistoryModel

logger = logging.getLogger(__name__)


class SQLAlchemyChatMessageHistory(BaseChatMessageHistory):
    """
    Chat message history backed by our own `ChatHistoryModel` SQLAlchemy model
    (table `message_store`), replacing LangChain's built-in
    `SQLChatMessageHistory`.

    Storing the messages via our own model (instead of the dynamically
    generated model LangChain creates internally) lets us persist additional
    columns - most notably a per-message `timestamp` - alongside each chat
    message.

    The public interface (`messages`, `add_message`, `clear`) intentionally
    mirrors `langchain_community.chat_message_histories.SQLChatMessageHistory`
    so that `Chatbot` (and any other caller) does not need to change.
    """

    def __init__(self, session_id: str, connection_string: str) -> None:
        self.session_id = session_id
        self.connection_string = connection_string
        self.engine = create_engine(connection_string, echo=False)
        self.sql_model_class = ChatHistoryModel
        self._create_table_if_not_exists()
        self.session_factory = sessionmaker(self.engine)

    def _create_table_if_not_exists(self) -> None:
        self.sql_model_class.metadata.create_all(self.engine)

    @property
    def messages(self) -> List[BaseMessage]:  # type: ignore[override]
        """Retrieve all messages for this session, ordered by insertion/timestamp."""
        with self.session_factory() as session:
            records = (
                session.query(self.sql_model_class)
                .where(self.sql_model_class.session_id == self.session_id)
                .order_by(self.sql_model_class.id.asc())
            )
            return [messages_from_dict([record.message])[0] for record in records]

    def add_message(self, message: BaseMessage) -> None:
        """Persist a single message (with its timestamp) to the database."""
        with self.session_factory() as session:
            session.add(
                self.sql_model_class(
                    session_id=self.session_id,
                    message=message_to_dict(message),
                )
            )
            session.commit()
            logger.debug("Persisted message for session_id=%s", self.session_id)

    def clear(self) -> None:
        """Remove all messages for this session from the database."""
        with self.session_factory() as session:
            session.query(self.sql_model_class).filter(
                self.sql_model_class.session_id == self.session_id
            ).delete()
            session.commit()
