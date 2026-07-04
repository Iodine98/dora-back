import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from chatdoc.chatbot import Chatbot


@pytest.fixture(name="mock_dependencies")
def fixture_mock_dependencies(monkeypatch):
    """
    Patches every external dependency that `Chatbot.__init__` touches (the
    vector database, embedding function, chat model, SQL-backed chat history,
    and the LangChain chain-construction helpers used to build the
    history-aware retrieval chain) so tests can assert on how `user_id` and
    `collection_name` are routed, and on how the chain is built/invoked,
    without needing a real embedding model, vector store, chat model, or
    database connection.

    Returns:
        dict: The patched classes/objects, keyed by name, so tests can assert
            on how they were called.
    """
    monkeypatch.setenv("CHAT_HISTORY_CONNECTION_STRING", "sqlite:///:memory:")
    monkeypatch.setenv("LAST_N_MESSAGES", "5")

    with patch("chatdoc.chatbot.EmbeddingFactory") as mock_embedding_factory, patch(
        "chatdoc.chatbot.VectorDatabase"
    ) as mock_vector_database, patch(
        "chatdoc.chatbot.SQLAlchemyChatMessageHistory"
    ) as mock_sql_chat_message_history, patch(
        "chatdoc.chatbot.ChatModel"
    ) as mock_chat_model, patch(
        "chatdoc.chatbot.create_history_aware_retriever"
    ) as mock_create_history_aware_retriever, patch(
        "chatdoc.chatbot.create_stuff_documents_chain"
    ) as mock_create_stuff_documents_chain, patch(
        "chatdoc.chatbot.create_retrieval_chain"
    ) as mock_create_retrieval_chain:
        mock_embedding_factory.return_value.create.return_value = MagicMock()
        mock_vector_database.return_value = MagicMock()
        mock_vector_database.return_value.retriever = MagicMock()

        mock_history_instance = mock_sql_chat_message_history.return_value
        mock_history_instance.messages = []
        mock_history_instance.add_message = MagicMock()

        mock_chat_model.return_value.chat_model = MagicMock()

        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock()
        mock_create_retrieval_chain.return_value = mock_chain

        yield {
            "EmbeddingFactory": mock_embedding_factory,
            "VectorDatabase": mock_vector_database,
            "SQLAlchemyChatMessageHistory": mock_sql_chat_message_history,
            "ChatModel": mock_chat_model,
            "create_history_aware_retriever": mock_create_history_aware_retriever,
            "create_stuff_documents_chain": mock_create_stuff_documents_chain,
            "create_retrieval_chain": mock_create_retrieval_chain,
            "mock_chain": mock_chain,
            "mock_history_instance": mock_history_instance,
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


def test_chatbot_builds_history_aware_retrieval_chain(mock_dependencies):
    """
    The chain construction should use the history-aware-retriever +
    retrieval-chain pattern (create_history_aware_retriever,
    create_stuff_documents_chain, create_retrieval_chain), replacing the
    deprecated `ConversationalRetrievalChain`.
    """
    chatbot = Chatbot(user_id="test-user")

    mock_dependencies["create_history_aware_retriever"].assert_called_once()
    mock_dependencies["create_stuff_documents_chain"].assert_called_once()
    mock_dependencies["create_retrieval_chain"].assert_called_once_with(
        mock_dependencies["create_history_aware_retriever"].return_value,
        mock_dependencies["create_stuff_documents_chain"].return_value,
    )
    assert chatbot.chatQA is mock_dependencies["mock_chain"]


def test_send_prompt_returns_answer_and_citations(mock_dependencies):
    """
    `send_prompt` should invoke the underlying retrieval chain with the
    prompt as `input` and the trimmed chat history, then surface the answer
    and citations derived from the retrieved `context` documents.
    """
    chatbot = Chatbot(user_id="test-user")

    source_document = Document(
        page_content="some proof text",
        metadata={"source": "/tmp/some-file.pdf", "page": 0, "ranking": 1, "score": 0.9},
    )
    mock_dependencies["mock_chain"].ainvoke.return_value = {
        "input": "What is DoRA?",
        "chat_history": [],
        "context": [source_document],
        "answer": "DoRA is a chatbot.",
    }

    result = asyncio.run(chatbot.send_prompt("What is DoRA?"))

    mock_dependencies["mock_chain"].ainvoke.assert_called_once_with(
        {"input": "What is DoRA?", "chat_history": []}
    )
    assert result["answer"] == "DoRA is a chatbot."
    assert result["citations"]["citations"][0]["source"] == "some-file.pdf"
    assert "source_documents" not in result
    assert "context" not in result


def test_send_prompt_persists_new_messages(mock_dependencies):
    """
    After answering, the human question and the AI answer (carrying the
    citations in its `additional_kwargs`) should both be persisted to the
    SQL-backed chat history.
    """
    chatbot = Chatbot(user_id="test-user")

    mock_dependencies["mock_chain"].ainvoke.return_value = {
        "input": "Hello",
        "chat_history": [],
        "context": [],
        "answer": "Hi there!",
    }

    asyncio.run(chatbot.send_prompt("Hello"))

    add_message_calls = mock_dependencies["mock_history_instance"].add_message.call_args_list
    assert len(add_message_calls) == 2

    human_message = add_message_calls[0].args[0]
    ai_message = add_message_calls[1].args[0]

    assert human_message.type == "human"
    assert human_message.content == "Hello"
    assert ai_message.type == "ai"
    assert ai_message.content == "Hi there!"
    assert "citations" in ai_message.additional_kwargs


def test_send_prompt_limits_chat_history_sent_to_chain(mock_dependencies):
    """
    Only the last `LAST_N_MESSAGES` messages should be forwarded to the
    retrieval chain as `chat_history`.
    """
    chatbot = Chatbot(user_id="test-user")
    chatbot.last_n_messages = 2
    chatbot.chat_history = ["msg1", "msg2", "msg3", "msg4"]

    mock_dependencies["mock_chain"].ainvoke.return_value = {
        "input": "Hello",
        "chat_history": [],
        "context": [],
        "answer": "Hi there!",
    }
    asyncio.run(chatbot.send_prompt("Hello"))

    call_kwargs = mock_dependencies["mock_chain"].ainvoke.call_args.args[0]
    assert call_kwargs["chat_history"] == ["msg3", "msg4"]
