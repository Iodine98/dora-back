from os import environ as os_environ
from typing import Any

from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages.base import messages_to_dict
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


from .vector_db import VectorDatabase
from .citation import Citations
from .chat_history import SQLAlchemyChatMessageHistory
from .embed.embedding_factory import EmbeddingFactory
from .chat_model import ChatModel
from .utils import Utils


CONTEXTUALIZE_QUESTION_SYSTEM_PROMPT = (
    "Given a chat history and the latest user question which might reference "
    "context in the chat history, formulate a standalone question which can be "
    "understood without the chat history. Do NOT answer the question, just "
    "reformulate it if needed and otherwise return it as is."
)

QUESTION_ANSWERING_SYSTEM_PROMPT = (
    "You are an assistant for question-answering tasks. Use the following "
    "pieces of retrieved context to answer the question. If you don't know "
    "the answer, say that you don't know."
    "\n\n"
    "{context}"
)


class Chatbot:
    """
    The chatbot class with a run method
    """

    def __init__(
        self,
        user_id: str,
        collection_name: str | None = None,
    ):
        """
        Args:
            user_id (str): Identifies the chat history for this user/session. Used
                exclusively to key the `SQLChatMessageHistory` conversation memory.
            collection_name (str | None): Identifies the vector store collection
                where the documents for this chat are stored. Used exclusively to
                select the `VectorDatabase` collection. Defaults to `user_id` when
                not provided, so a single caller-supplied identifier can still be
                used for both without breaking existing behavior.
        """
        self.user_id = user_id
        self.collection_name = collection_name if collection_name is not None else user_id
        self.embedding_fn = EmbeddingFactory().create()
        self.vector_db = VectorDatabase(self.collection_name, self.embedding_fn)
        self.memory_db = SQLAlchemyChatMessageHistory(self.user_id, Utils.get_env_variable("CHAT_HISTORY_CONNECTION_STRING"))
        self.chat_model: BaseChatModel = ChatModel().chat_model
        self.chatQA = self._build_chatqa_chain()  # pylint: disable=invalid-name
        self.chat_history = self.memory_db.messages
        self.last_n_messages = int(os_environ.get("LAST_N_MESSAGES", 5))

    def _build_chatqa_chain(self):
        """
        Build the retrieval chain used to answer questions using the chat history.

        This replaces the deprecated `ConversationalRetrievalChain` with the
        history-aware-retriever + retrieval-chain pattern described in the
        LangChain "Add chat history" guide.
        """
        contextualize_question_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CONTEXTUALIZE_QUESTION_SYSTEM_PROMPT),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        history_aware_retriever = create_history_aware_retriever(
            self.chat_model, self.vector_db.retriever, contextualize_question_prompt
        )

        question_answering_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", QUESTION_ANSWERING_SYSTEM_PROMPT),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        question_answer_chain = create_stuff_documents_chain(self.chat_model, question_answering_prompt)

        return create_retrieval_chain(history_aware_retriever, question_answer_chain)

    async def send_prompt(self, prompt: str) -> dict[str, Any]:
        """
        Method to send a prompt to the chatbot

        Uses the chain's async `ainvoke` so that the (slow) LLM completion and
        retrieval calls don't block the Flask worker's event loop.
        """
        previous_messages = self.chat_history[-self.last_n_messages :]
        chain_result = await self.chatQA.ainvoke({"input": prompt, "chat_history": previous_messages})
        source_documents = chain_result["context"]
        citations = Citations(source_documents)
        citations_dict = citations.__dict__()

        human_message = HumanMessage(content=prompt)
        ai_message = AIMessage(content=chain_result["answer"], additional_kwargs={"citations": citations_dict})
        for message in (human_message, ai_message):
            self.memory_db.add_message(message)
        self.chat_history = self.memory_db.messages

        return {
            "answer": chain_result["answer"],
            "citations": citations_dict,
            "chat_history": messages_to_dict(self.chat_history),
        }
