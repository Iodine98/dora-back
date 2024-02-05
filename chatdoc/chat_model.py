import json
from langchain_community.chat_models.azureml_endpoint import AzureMLChatOnlineEndpoint
from langchain_community.chat_models import ChatOpenAI
from langchain_core.pydantic_v1 import SecretStr
from langchain_core.language_models.chat_models import BaseChatModel
from pathlib import Path
from .utils import Utils
from .local_llm import build_llm


class ChatModel:
    """
    A class representing a chat model.

    Attributes:
        chat_model (object): The chat model.

    Methods:
        __init__(): Initializes the ChatModel object by setting
          the chat model.
    """

    def _load_chat_model(self) -> BaseChatModel:
        """
        Loads the embedding function based on the vendor name.

        Returns:
            object: The embedding function.

        Raises:
            ValueError: If the vendor name is invalid.
        """
        match self.vendor_name:
            case "openai":
                if self.api_key is None:
                    self.api_key = Utils.get_env_variable("OPENAI_API_KEY")
                return ChatOpenAI(api_key=self.api_key, model=self.chat_model_name)
            case "huggingface":
                if self.api_key is None:
                    self.api_key = Utils.get_env_variable("HUGGINGFACE_API_KEY")
                raise NotImplementedError("HuggingFace chat model not implemented")
            case "azureml":
                if self.api_key is None:
                    self.api_key = Utils.get_env_variable("AZUREML_API_KEY")
                with open("../azure_chat_models.json", "r", encoding="utf-8") as azure_chat_models_file:
                    azure_chat_models = json.load(azure_chat_models_file)
                if self.chat_model_name not in azure_chat_models:
                    raise ValueError("Invalid Azure ML chat model name")
                chat_model_url = azure_chat_models[self.chat_model_name]
                return AzureMLChatOnlineEndpoint(endpoint_api_key=SecretStr(self.api_key), endpoint_url=chat_model_url)
            case "local":
                model_path = str(Path(Utils.get_env_variable("CHAT_MODEL_FOLDER_PATH")) / self.chat_model_name)
                return build_llm(
                    model_path=model_path,
                    length=128,  # TODO: Change this to env variable
                    temp=0,
                    gpu_layers=5,  # TODO: Change this to env variable
                    chat_box=None,  # TODO: Change this to env variable
                )
            case _:
                raise ValueError("Invalid vendor name")

    def __init__(
        self,
        chat_model_vendor_name: str | None = None,
        chat_model_name: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """
        Initializes the ChatModel object by setting
        the chat model.
        """
        self.vendor_name: str = (
            chat_model_vendor_name
            if chat_model_vendor_name is not None
            else Utils.get_env_variable("CHAT_MODEL_VENDOR_NAME")
        )
        self.chat_model_name = (
            chat_model_name if chat_model_name is not None else Utils.get_env_variable("CHAT_MODEL_NAME")
        )
        self.api_key = api_key
        self.chat_model: BaseChatModel = self._load_chat_model()
