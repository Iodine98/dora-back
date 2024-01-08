import os
import pytest
from langchain.chat_models.openai import ChatOpenAI
from chatdoc.chat_model import ChatModel


@pytest.fixture(name="openai_chat_model")
def openai_chat_model_fixture():
    """
    Function to test the chat model with OpenAI vendor.

    Returns:
        ChatModel: An instance of the ChatModel class.

    """
    yield ChatModel(chat_model_vendor_name="openai", chat_model_name="gpt-3", api_key="test")


def test_set_vendor_name(openai_chat_model):
    """
    Test case to verify the `vendor_name` property of the `chat_model_openai` object.

    Args:
        monkeypatch: Monkeypatch fixture for patching objects during testing.
        chat_model_openai: Instance of the `ChatModel` class with the 'openai' vendor name.

    Returns:
        None
    """
    assert openai_chat_model.vendor_name == "openai"


def test_set_chat_model_name(openai_chat_model):
    """
    Test case to verify if the chat model name is set correctly.

    Args:
        chat_model_openai: An instance of the ChatModelOpenAI class.

    Returns:
        None
    """
    assert openai_chat_model.chat_model_name == "gpt-3"


def test_load_chat_model_openai(openai_chat_model):
    """
    Test case for loading the chat model from OpenAI.

    Args:
        chat_model_openai (MagicMock): The chat model object.

    Returns:
        None
    """
    assert isinstance(openai_chat_model.chat_model, ChatOpenAI)


def test_load_chat_model_huggingface():
    """
    Test case for the _load_chat_model method of the chat_model_huggingface object.
    It checks if a NotImplementedError is raised when calling the _load_chat_model method.
    """
    with pytest.raises(NotImplementedError):
        ChatModel(chat_model_vendor_name="huggingface", chat_model_name="BloombergGPT", api_key="test")


def test_load_chat_model_invalid_vendor():
    """
    Test case to ensure that loading a chat model with an invalid vendor raises a ValueError.
    """
    with pytest.raises(ValueError):
        ChatModel(chat_model_vendor_name="mistral", chat_model_name="mistral-7B")


def test_missing_openai_api_key():
    """
    Test case to ensure that a ValueError is raised when the OpenAI API key is not set.
    """
    if "OPENAI_API_KEY" in os.environ:
        assert isinstance(
            ChatModel(chat_model_vendor_name="openai", chat_model_name="gpt-3").chat_model,
              ChatOpenAI) 
    else:
        with pytest.raises(ValueError):
            ChatModel(chat_model_vendor_name="openai", chat_model_name="gpt-3")



def test_missing_huggingface_api_key():
    """
    Test case to ensure that a ValueError is raised when the HuggingFace API key is not set.
    """
    with pytest.raises(ValueError):
        ChatModel(chat_model_vendor_name="huggingface", chat_model_name="BloombergGPT")
