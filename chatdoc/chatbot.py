from typing import Any
import time

from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models.base import BaseChatModel
from langchain.memory import ConversationBufferMemory


from .vector_db import VectorDatabase
from .citation import Citations
from .embed.embedding_factory import EmbeddingFactory
from .chat_model import ChatModel


class Chatbot:
    """
    The chatbot class with a run method
    """

    def __init__(
        self,
        user_id: str,
    ):
        self.user_id = user_id
        self.embedding_fn = EmbeddingFactory().create()
        self.vector_db = VectorDatabase(self.user_id, self.embedding_fn)
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key="answer")
        self.chat_model: BaseChatModel = ChatModel().chat_model
        self.chatQA = ConversationalRetrievalChain.from_llm(  # pylint: disable=invalid-name
            llm=self.chat_model,
            retriever=self.vector_db.retriever,
            memory=self.memory,
            return_source_documents=True,
        )
        self.chat_history: list[tuple[str, str, Citations]] = []
        self.last_n_messages = 5  # TODO: Change into environment variable

    def send_prompt(self, prompt: str) -> dict[str, Any]:
        """
        Method to send a prompt to the chatbot
        """
        result = self.chatQA({"question": prompt, "chat_history": self.chat_history[-self.last_n_messages :]})
        citations: Citations = Citations(set(), True)
        citations.get_unique_citations(result["source_documents"])
        self.chat_history.append((prompt, result["answer"], citations))
        result["chat_history"] = [message.dict() for message in result["chat_history"]]
        result["source_documents"] = [source_document.dict() for source_document in result["source_documents"]]
        result["citations"] = citations.__dict__()
        return result
