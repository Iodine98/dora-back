"""
Module definine the VectorDatabase class
"""
import os
from typing import TypedDict
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
    """

    k: int
    score_threshold: float
    fetch_k: int


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
            persist_directory="./chroma_db"
        )
        self.search_kwargs = self.load_search_kwargs()
        self.retriever = self.chroma_instance.as_retriever(**self.search_kwargs)

    def load_search_kwargs(
        self, top_k_documents_default=5, minimum_accuracy_default=0.80, fetch_k_default=100
    ) -> SearchArgs:
        """
        Load search kwargs from the config file
        """
        top_k_documents = os.environ.get("TOP_K_DOCUMENTS", top_k_documents_default)
        minimum_accuracy = os.environ.get("MINIMUM_ACCURACY", minimum_accuracy_default)
        fetch_k_documents = os.environ.get("FETCH_K_DOCUMENTS", fetch_k_default)
        search_kwargs: SearchArgs = {
            "k": int(top_k_documents),
            "score_threshold": float(minimum_accuracy),
            "fetch_k": int(fetch_k_documents),
        }
        return search_kwargs

    def get_retriever_settings(self) -> SearchArgs:
        """
        Get the retriever settings
        """
        return self.search_kwargs

    def update_retriever_settings(self, search_kwargs: SearchArgs) -> None:
        """
        Update the retriever settings
        """
        self.search_kwargs = search_kwargs
        self.retriever = self.chroma_instance.as_retriever(search_kwargs=search_kwargs)

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
