from typing import Any
from langchain.schema.embeddings import Embeddings
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain.embeddings.huggingface import HuggingFaceInferenceAPIEmbeddings
import httpx
from ..utils import Utils


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

    def __init__(self, vendor_name: str | None = None, embedding_model_name: str | None = None, http_client: httpx.Client | None = None) -> None:
        """
        Initializes an instance of the EmbeddingFactory class.

        Args:
            vendor_name (str | None, optional): The name of the vendor. Defaults to None.
            embedding_model_name (str | None, optional): The name of the embedding model. Defaults to None.

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
        self.http_client = http_client
        self.api_key = self._get_api_key()

    def _get_api_key(self, api_key: str | None = None) -> str:
        if "local" in self.vendor_name:
            return ""
        if api_key is None:
            api_key_var = self.api_key_map.get(self.vendor_name)
            if api_key_var is None:
                raise ValueError(f"No API key environment variable available for vendor name {self.vendor_name}")
            api_key = Utils.get_env_variable(api_key_var)
            if api_key is None:
                raise ValueError(f"No API key available for variable name {api_key_var}")
        return api_key

    def _create_settings_dict(self, defaults: bool = True, overwrite: dict | None = None) -> dict[str, Any]:
        """
        Loads the settings for the specified vendor name.

        Raises:
            ValueError: If no settings are available for the specified vendor name.

        """
        is_empty = lambda dicto: (isinstance(dicto, dict) and len(dicto) == 0)
        if not defaults:
            if overwrite is None or is_empty(overwrite):
                raise ValueError("Overwriting settings dictionary cannot be empty when defaults are False.")
            return overwrite
        
        settings_dict = {}
        match self.vendor_name:
            case "openai":
                settings_dict = {
                    "disallowed_special": (),
                    "show_progress_bar": True,
                }
            case _:
                pass
        return settings_dict

    def _create_model_name_dict(self) -> dict[str, str]:
        """
        Loads the model name for the specified vendor name.

        Raises:
            ValueError: If no model name is available for the specified vendor name.

        """
        key: str
        match self.vendor_name:
            case "openai":
                key = "model"
            case "huggingface" | "huggingface_local":
                key = "model_name"
            case _:
                key = "model_name"
        return {key: self.embedding_model_name}

    def create(self) -> Embeddings:
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
        settings_dict = self._create_settings_dict()
        model_name_dict = self._create_model_name_dict()
        return embedding_class(**model_name_dict, **settings_dict, api_key=self._get_api_key(), http_async_client=self.http_client)
