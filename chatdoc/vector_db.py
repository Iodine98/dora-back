"""
Module definine the VectorDatabase class
"""
import os
from typing import Literal, TypedDict
from langchain.embeddings.base import Embeddings
from langchain.schema import Document
from langchain.vectorstores.chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
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


class CustomVectorStoreRetriever(VectorStoreRetriever):
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        if self.search_type == "similarity":
            docs = self.vectorstore.similarity_search(query, **self.search_kwargs)
        elif self.search_type == "similarity_score_threshold":
            docs_and_similarities = (
                self.vectorstore.similarity_search_with_relevance_scores(
                    query, **self.search_kwargs
                )
            )
            docs_and_similarities.sort(key=lambda doc_sim: doc_sim[1], reverse=True)
            for doc, similarity in docs_and_similarities:
                doc.metadata["score"] = similarity
            docs = [doc for doc, _ in docs_and_similarities]
        elif self.search_type == "mmr":
            docs = self.vectorstore.max_marginal_relevance_search(
                query, **self.search_kwargs
            )
        else:
            raise ValueError(f"search_type of {self.search_type} not allowed.")
        for i, doc in enumerate(docs):
            doc.metadata["ranking"] = i + 1
        return docs

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
        self.retriever = CustomVectorStoreRetriever(
            vectorstore=self.chroma_instance,
            **self.retriever_settings, # type: ignore
        )

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

    async def add_documents(self, documents: list[Document]) -> list[str]:
        """
        Add multiple documents to the vector database.

        Args:
            documents (list[Document]):
                A list of Document objects to be added when this endpoint is called from `server.py`.

        Returns:
            document_ids (list[str]):
                A list of document IDs for the documents that were added.
        """
        document_ids: list[str] = await self.chroma_instance.aadd_documents(documents)
        self.chroma_instance.persist()
        return document_ids

    async def delete_documents(self, document_ids: list[str]) -> bool:
        """
        Delete a document from the vector database.

        Args:
            document_ids (str):
                A list of document IDs to be deleted

        Returns:
            None
        """
        try:
            self.chroma_instance.delete(document_ids)
            self.chroma_instance.persist()
        except Exception as ChromaError:
            raise Exception(f"Error deleting document: {ChromaError}")
        return True
