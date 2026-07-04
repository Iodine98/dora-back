from unittest.mock import MagicMock, patch

import pytest

from chatdoc.chatbot import Chatbot


@pytest.fixture(name="mock_dependencies")
def fixture_mock_dependencies(monkeypatch):
    """
    Patches every external dependency that `Chatbot.__init__` touches so that
    tests can assert on how `user_id` and `collection_name` are routed without
    needing a real embedding model, vector store, chat model, or database
    connection.

    Returns:
        dict: The patched classes/objects, keyed by name, so tests can assert
            on how they were called.
    """
    monkeypatch.setenv("CHAT_HISTORY_CONNECTION_STRING", "sqlite:///:memory:")

    with patch("chatdoc.chatbot.EmbeddingFactory") as mock_embedding_factory, patch(
        "chatdoc.chatbot.VectorDatabase"
    ) as mock_vector_database, patch(
        "chatdoc.chatbot.SQLAlchemyChatMessageHistory"
    ) as mock_sql_chat_message_history, patch(
        "chatdoc.chatbot.ChatModel"
    ) as mock_chat_model, patch(
        "chatdoc.chatbot.ConversationalRetrievalChain"
    ) as mock_conversational_retrieval_chain:
        mock_embedding_factory.return_value.create.return_value = MagicMock()
        mock_vector_database.return_value = MagicMock()
        mock_sql_chat_message_history.return_value = MagicMock(messages=[])
        mock_chat_model.return_value.chat_model = MagicMock()
        mock_conversational_retrieval_chain.from_llm.return_value = MagicMock()
        yield {
            "EmbeddingFactory": mock_embedding_factory,
            "VectorDatabase": mock_vector_database,
            "SQLAlchemyChatMessageHistory": mock_sql_chat_message_history,
            "ChatModel": mock_chat_model,
            "ConversationalRetrievalChain": mock_conversational_retrieval_chain,
        }


def test_collection_name_defaults_to_user_id(mock_dependencies):
    """
    When no `collection_name` is supplied, the `Chatbot` should fall back to
    using `user_id` for both the chat history session and the vector store
    collection, preserving the previous behavior for existing callers.
    """
    chatbot = Chatbot(user_id="user-123")

    assert chatbot.user_id == "user-123"
    assert chatbot.collection_name == "user-123"
    mock_dependencies["VectorDatabase"].assert_called_once_with(
        "user-123", mock_dependencies["EmbeddingFactory"].return_value.create.return_value
    )
    mock_dependencies["SQLAlchemyChatMessageHistory"].assert_called_once_with(
        "user-123", "sqlite:///:memory:"
    )


def test_collection_name_used_independently_from_user_id(mock_dependencies):
    """
    When `collection_name` is supplied explicitly and differs from `user_id`,
    the vector store should be keyed by `collection_name` while the chat
    history should still be keyed by `user_id`.
    """
    chatbot = Chatbot(user_id="user-123", collection_name="collection-abc")

    assert chatbot.user_id == "user-123"
    assert chatbot.collection_name == "collection-abc"
    mock_dependencies["VectorDatabase"].assert_called_once_with(
        "collection-abc", mock_dependencies["EmbeddingFactory"].return_value.create.return_value
    )
    mock_dependencies["SQLAlchemyChatMessageHistory"].assert_called_once_with(
        "user-123", "sqlite:///:memory:"
    )
