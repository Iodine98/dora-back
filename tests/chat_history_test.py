import pytest
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import select

from chatdoc.chat_history import SQLAlchemyChatMessageHistory
from server_modules.models import ChatHistoryModel


@pytest.fixture(name="connection_string")
def connection_string_fixture(tmp_path):
    """
    A file-based SQLite connection string, unique per test, so that multiple
    `SQLAlchemyChatMessageHistory` instances (each opening their own engine)
    still share the same underlying database - mirroring how, in production,
    multiple requests connect to the same chat-history database.
    """
    yield f"sqlite:///{tmp_path / 'chat_history.db'}"


@pytest.fixture(name="chat_history")
def chat_history_fixture(connection_string):
    """
    Fixture that creates a `SQLAlchemyChatMessageHistory` backed by a
    temporary SQLite database, isolated per test.
    """
    yield SQLAlchemyChatMessageHistory("test-session", connection_string)


def test_messages_empty_by_default(chat_history):
    """
    A freshly created chat history should have no messages.
    """
    assert not chat_history.messages


def test_add_message_persists_message(chat_history):
    """
    Adding a message should make it retrievable via the `messages` property,
    preserving type and content.
    """
    chat_history.add_message(HumanMessage(content="Hello there"))
    messages = chat_history.messages
    assert len(messages) == 1
    assert isinstance(messages[0], HumanMessage)
    assert messages[0].content == "Hello there"


def test_add_message_persists_timestamp(chat_history):
    """
    Each persisted message should get a non-null `timestamp` set by the
    database (server-side default), so message ordering/age can be tracked.
    """
    chat_history.add_message(HumanMessage(content="Hello there"))
    with chat_history.session_factory() as session:
        record = session.execute(
            select(ChatHistoryModel).where(ChatHistoryModel.session_id == "test-session")
        ).scalar_one()
        assert record.timestamp is not None


def test_messages_are_ordered_and_isolated_per_session(chat_history):
    """
    Messages should be returned in insertion order, and messages belonging to
    another session id should not leak in.
    """
    other_history = SQLAlchemyChatMessageHistory("other-session", chat_history.connection_string)
    chat_history.add_message(HumanMessage(content="first"))
    other_history.add_message(HumanMessage(content="should not appear"))
    chat_history.add_message(AIMessage(content="second"))

    messages = chat_history.messages
    assert [message.content for message in messages] == ["first", "second"]


def test_clear_removes_all_messages(chat_history):
    """
    Clearing the history should remove all messages for that session.
    """
    chat_history.add_message(HumanMessage(content="Hello there"))
    chat_history.add_message(AIMessage(content="Hi!"))
    assert len(chat_history.messages) == 2

    chat_history.clear()
    assert not chat_history.messages
