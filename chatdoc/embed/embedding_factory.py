from typing import Any, Optional
import httpx
import openai
from langchain.schema.embeddings import Embeddings
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain.embeddings.huggingface import HuggingFaceInferenceAPIEmbeddings
from ..utils import Utils
from ..http_client import HttpClientFactory


class EmbeddingFactory:
    """
    Factory class for creating different types of embeddings.

    Attributes:
        embedding_map (dict[str, type[Embeddings]]): A mapping of vendor names to embedding classes.
        api_key_map (dict[str, str]): A mapping of vendor names to API key environment variable names.

    Methods:
        create(vendor_name: str, embedding_model_name: str, api_key: str | None = None) -> Embeddings:
            Creates an instance of the specified embedding class.

    """

    def __init__(
        self,
        vendor_name: str | None = None,
        embedding_model_name: str | None = None,
        http_client: Optional[httpx.Client] = None,
        http_async_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """
        Initializes an instance of the EmbeddingFactory class.

        Args:
            vendor_name (str | None, optional): The name of the vendor. Defaults to None.
            embedding_model_name (str | None, optional): The name of the embedding model. Defaults to None.
            http_client (Optional[httpx.Client], optional): The (sync) HTTP client used to
                talk to vendor APIs that support it (e.g. OpenAI). Defaults to the shared
                client from ``HttpClientFactory``.
            http_async_client (Optional[httpx.AsyncClient], optional): The async HTTP
                client counterpart of ``http_client``. Defaults to the shared async
                client from ``HttpClientFactory``.

        """
        self.embedding_map: dict[str, type[Embeddings]] = {
            "openai": OpenAIEmbeddings,
            "huggingface": HuggingFaceInferenceAPIEmbeddings,
            "huggingface_local": HuggingFaceEmbeddings,
        }
        self.api_key_map: dict[str, str] = {
            "openai": "OPENAI_API_KEY",
            "huggingface": "HUGGINGFACE_API_KEY",
        }
        self.vendor_name = vendor_name if vendor_name is not None else Utils.get_env_variable("EMBEDDING_MODEL_VENDOR_NAME")
        self.embedding_model_name = (
            embedding_model_name if embedding_model_name is not None else Utils.get_env_variable("EMBEDDING_MODEL_NAME")
        )
        self.http_client: httpx.Client = (
            http_client if http_client is not None else HttpClientFactory.get_shared_client()
        )
        self.http_async_client: httpx.AsyncClient = (
            http_async_client if http_async_client is not None else HttpClientFactory.get_shared_async_client()
        )

    def _create_api_key_dict(self, api_key: str | None) -> dict[str, Any]:
        if api_key is None and "local" not in self.vendor_name:
            api_key_var = self.api_key_map.get(self.vendor_name)
            if api_key_var is None:
                raise ValueError(f"No API key environment variable available for vendor name {self.vendor_name}")
            api_key = Utils.get_env_variable(api_key_var)
        return {"api_key": api_key} if "local" not in self.vendor_name else {}

    def _create_settings_dict(self) -> dict[str, Any]:
        """
        Loads the settings for the specified vendor name.

        Raises:
            ValueError: If no settings are available for the specified vendor name.

        """
        settings_dict = {}
        match self.vendor_name:
            case "openai":
                settings_dict["disallowed_special"] = ()
            case _:
                pass
        return settings_dict

    def _create_model_name_dict(self) -> dict[str, str]:
        """
        Loads the model name for the specified vendor name.

        Raises:
            ValueError: If no model name is available for the specified vendor name.

        """
        model_name_dict = {}
        match self.vendor_name:
            case "openai":
                model_name_dict["model"] = self.embedding_model_name
            case "huggingface" | "huggingface_local":
                model_name_dict["model_name"] = self.embedding_model_name
            case _:
                model_name_dict["model_name"] = self.embedding_model_name
        return model_name_dict

    def _create_client_dict(self, api_key: str | None) -> dict[str, Any]:
        """
        Builds already-instantiated OpenAI sync/async clients (wrapping our
        injected/shared HTTP client(s)) for vendors whose embedding class
        supports it (currently only OpenAI).

        NOTE: `OpenAIEmbeddings` forwards a single `http_client` kwarg to
        *both* the sync `openai.OpenAI` and the async `openai.AsyncOpenAI`
        client it builds internally, but each of those requires a
        differently-typed httpx client (`httpx.Client` vs.
        `httpx.AsyncClient`). To still allow injecting our shared,
        configurable HTTP client(s), we build the underlying OpenAI clients
        ourselves and hand `OpenAIEmbeddings` their already-instantiated
        `client`/`async_client` attributes instead.

        Returns:
            dict[str, Any]: A kwargs dict containing `client`/`async_client`,
                or an empty dict for vendors that don't support it.
        """
        if self.vendor_name != "openai":
            return {}
        return {
            "client": openai.OpenAI(api_key=api_key, http_client=self.http_client).embeddings,
            "async_client": openai.AsyncOpenAI(api_key=api_key, http_client=self.http_async_client).embeddings,
        }

    def create(self, api_key: str | None = None) -> Embeddings:
        """
        Creates an instance of the specified embedding class.

        Args:
            api_key (str | None, optional): The API key to be used. Defaults to None.

        Returns:
            Embeddings: An instance of the specified embedding class.

        Raises:
            ValueError: If no embedding is available for the specified vendor name.

        """
        embedding_class = self.embedding_map.get(self.vendor_name)
        if embedding_class is None:
            raise ValueError(f"No embedding available for vendor name {self.vendor_name}")
        api_key_dict = self._create_api_key_dict(api_key)
        settings_dict = self._create_settings_dict()
        model_name_dict = self._create_model_name_dict()
        client_dict = self._create_client_dict(api_key_dict.get("api_key"))
        return embedding_class(**model_name_dict, **settings_dict, **api_key_dict, **client_dict)
