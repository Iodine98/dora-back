from typing import TypedDict, Any


class Identity(TypedDict):
    """
    Represents the identity of a user.

    Attributes:
        sessionId (str): The session ID of the user.
        authenticated (bool): Indicates whether the user is authenticated.
        hasDB (bool): Indicates whether the user has a database.
    """

    sessionId: str
    authenticated: bool
    hasDB: bool


class ResponseMessage(TypedDict):
    """
    Represents a response message.

    Attributes:
        message (str): The message.
        error (str): The error message if applicable, else it's an empty string.
    """

    message: str
    error: str


class IdentifyResponse(ResponseMessage, Identity):
    """
    Represents a response for identity identification.
    """


class UploadResponse(ResponseMessage):
    """
    Represents a response for uploading files.
    """

    file_id_mapping: dict[str, list[str]]


class PromptResponse(ResponseMessage):
    """
    Represents a response for a prompt.
    """

    result: dict[str, Any]
