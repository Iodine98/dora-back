"""
Module definine the VectorDatabase class
"""
import os
from typing import Literal, TypedDict
from langchain.embeddings.base import Embeddings
from langchain.schema import Document
from langchain.vectorstores.chroma import Chroma
from chromadb import PersistentClient
from chromadb.api import ClientAPI


class SearchArgs(TypedDict, total=True):
    """
    Represents the arguments for a search operation.

    Attributes:
        k (int): The number of top documents to return.
        score_threshold (float): The threshold score for documents to be included in the results.
        fetch_k (int): The total number of documents to fetch from the database.
        lambda_mult (float): The lambda multiplier for the MMR algorithm.
    """

    k: int
    score_threshold: float
    fetch_k: int
    lambda_mult: float


class RetrieverSettings(TypedDict, total=True):
    """
    Represents the arguments for a search operation.

    Attributes:
        search_kwargs (SearchArgs): The arguments for a search operation.
        search_type (str): The search strategy to use.
    """

    search_kwargs: SearchArgs
    search_type: str


class VectorDatabase:
    """
    The VectorDatabase class that creates a ChromaDB store locally
    """

    _instance = None

    _chroma_db_client = None

    @property
    def chroma_client(self) -> ClientAPI:
        """
        ChromaDB client
        """
        if self._chroma_db_client is not None:
            return self._chroma_db_client
        dora_env = os.environ.get("CURRENT_ENV")
        match dora_env:
            case "DEV" | "TST":
                self._chroma_db_client = PersistentClient()
            case "PROD":
                # Connect to ChromaDB in the cloud
                # Add code here to connect to ChromaDB in the cloud
                raise NotImplementedError("ChromaDB in the cloud not implemented yet")
            case _:
                raise ValueError("Invalid DORA environment")
        return self._chroma_db_client

    def __init__(self, collection_name: str, embedding_fn: Embeddings) -> None:
        self.collection_name = collection_name
        self.chroma_instance = Chroma(
            collection_name=collection_name,
            client=self.chroma_client,
            embedding_function=embedding_fn,
            persist_directory="./chroma_db",
        )
        self.retriever_settings: RetrieverSettings = self.load_retriever_settings()
        self.retriever = self.chroma_instance.as_retriever(**self.retriever_settings)

    def load_retriever_settings(
        self,
        top_k_documents_default=5,
        minimum_accuracy_default=0.80,
        fetch_k_default=100,
        strategy_default="mmr",
        lambda_mult_default=0.2,
    ) -> RetrieverSettings:
        """
        Load search kwargs from the config file
        """
        top_k_documents = os.environ.get("TOP_K_DOCUMENTS", top_k_documents_default)
        minimum_accuracy = os.environ.get("MINIMUM_ACCURACY", minimum_accuracy_default)
        fetch_k_documents = os.environ.get("FETCH_K_DOCUMENTS", fetch_k_default)
        lambda_mult = os.environ.get("LAMBDA_MULT", lambda_mult_default)
        strategy = os.environ.get("STRATEGY", strategy_default)
        search_kwargs: SearchArgs = {
            "k": int(top_k_documents),
            "score_threshold": float(minimum_accuracy),
            "fetch_k": int(fetch_k_documents),
            "lambda_mult": float(lambda_mult),
        }
        return {
            "search_kwargs": search_kwargs,
            "search_type": strategy,
        }

    def get_retriever_settings(self) -> RetrieverSettings:
        """
        Get the retriever settings
        """
        return self.retriever_settings

    def update_retriever_settings(self, retriever_settings: RetrieverSettings) -> None:
        """
        Update the retriever settings
        """
        self.retriever_settings = retriever_settings
        self.retriever = self.chroma_instance.as_retriever(**retriever_settings)

    async def add_documents(self, documents: list[Document]) -> None:
        """
        Add multiple documents to the vector database.

        Args:
            documents (list[Document]):
                A list of Document objects to be added when this endpoint is called from `server.py`.

        Returns:
            None
        """
        await self.chroma_instance.aadd_documents(documents)
        self.chroma_instance.persist()
