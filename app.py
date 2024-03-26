# system imports
import base64
import io
import time
import uuid
import json
from typing import Any, cast

# third party imports
from flask import Flask, request, session, make_response, Response

from flask_cors import CORS

# local imports
from server_modules import set_logging_config
from server_modules.methods import ServerMethods
from server_modules.models import add_new_record, update_record_with_answers
from server_modules.class_defs import (
    IdentifyResponse,
    Identity,
    ResponseMessage,
    PromptResponse,
    UploadResponse,
    ChatHistoryResponse,
    WEMUploadResponse,
)
from chatdoc.chatbot import Chatbot
from chatdoc.utils import Utils
from langchain_core.messages.base import messages_to_dict
from langchain_community.chat_message_histories import SQLChatMessageHistory
from werkzeug.datastructures import FileStorage

set_logging_config(Utils.get_env_variable("LOGGING_FILE_PATH"))


app = Flask(__name__)
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True

current_env = Utils.get_env_variable("CURRENT_ENV")
match current_env:
    case "DEV":
        CORS(app)
        app.logger.info(msg="Running in development mode")
    case "TST":
        app.logger.info(msg="Running in test mode")
    case "PROD":
        app.logger.info(msg="Running in production mode")
    case _:
        raise ValueError("Invalid environment variable set for CURRENT_ENV")

app.secret_key = str(uuid.uuid4())
sm_app = ServerMethods(app)


Basic = str | int | float | bool
Property = Basic | dict | tuple | list


def get_property(
    property_name: str, with_error=True, property_type: type[Property] = str
) -> Any:
    """
    Gets a property from the request object.

    Args:
        property_name (str): The name of the property to get from the request object.

    Raises:
        ValueError: If the property is not found in the request object.

    Returns:
        str: The property value.
    """
    property_value: str = ""
    if property_name in session:
        property_value = session[property_name]
    elif property_name in request.form:
        property_value = request.form[property_name]
    elif (json_payload := request.json) is not None:
        if isinstance(json_payload, dict) and property_name in json_payload:
            property_value = json.dumps(json_payload[property_name], ensure_ascii=False)
        elif isinstance(json_payload, list):
            for item in json_payload:
                if isinstance(item, dict) and property_name in item:
                    property_value = json.dumps(item[property_name], ensure_ascii=False)
                    break
            else:
                if with_error:
                    raise ValueError(f"No {property_name} found in request.json")
    elif with_error:
        raise ValueError(
            f"No {property_name} found in request.form, session, or request.json"
        )
    if property_type == str:
        return str(property_value).replace("\"", "")
    if issubclass(property_type, Basic):
        return cast(property_type, property_value)
    return json.loads(property_value)


@app.errorhandler(Exception)
def handle_value_error(error: Exception) -> Response:
    """
    Handles an Exception.

    Args:
        error (Exception): The Exception to handle.

    Returns:
        Response: A response object containing the error message and status code.
    """
    response_message = ResponseMessage(message="", error=str(error))
    return make_response(response_message, 400)


@app.after_request
def add_cors_headers(response: Response) -> Response:
    """
    Adds CORS headers to the response object.

    Args:
        response (Response): The response object to add CORS headers to.

    Returns:
        Response: The response object with CORS headers added.
    """
    current_host_port = "127.0.0.1:5000"
    origin = request.headers.get("Origin")
    host = request.headers.get("Host")
    if host != current_host_port:
        if origin is not None:
            response_message = ResponseMessage(
                message="", error="No origin header found"
            )
            return make_response(response_message, 400)
    if host == current_host_port:
        origin = host
    response.headers["Access-Control-Allow-Origin"] = str(origin)
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


@app.route("/upload_files", methods=["OPTIONS"])
@app.route("/prompt", methods=["OPTIONS"])
def set_post_options() -> Response:
    """
    Handles the OPTIONS request for the upload_files route.

    Returns:
        Response: A response object containing the CORS headers.
    """
    response = make_response("OPTIONS OK", 200)
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST"
    return response


@app.route("/", methods=["GET"])
def root() -> Response:
    """
    Returns a generic welcome for Gunicorn to load
    """
    return make_response("<h1>Welcome to our server !!</h1>", 200)


@app.route("/identify", methods=["POST"])
def identify() -> Response:
    """
    Identifies the user and returns a response object.

    Returns:
        dict: A response object containing the sessionId and message.
    """
    if (session_id := get_property("sessionId", with_error=False)) and isinstance(
        session_id, str
    ):
        identity = Identity(
            sessionId=session_id,
            authenticated=True,
            hasDB=bool(get_property("hasDB", with_error=False, property_type=bool)),
        )
        identify_response = IdentifyResponse(
            message=f"Welcome back user: {session_id} !", error="", **identity
        )
    else:
        identity = Identity(
            sessionId=str(uuid.uuid4()), authenticated=True, hasDB=False
        )
        identify_response = IdentifyResponse(
            message=f"Welcome new user: {identity['sessionId']} !", error="", **identity
        )
    add_new_record(identity["sessionId"], app.logger)
    session.update(identity)
    response = make_response(identify_response, 200)
    return response


@app.route("/upload_files_json", methods=["POST"])
async def upload_files_json() -> Response:
    """
    Uploads files to the server.

    Returns:
        str: Success message indicating the number of files uploaded.
        tuple: Error message and status code if user is not authenticated.
    """

    def get_prefix() -> str:
        if "prefix" in file_dict:
            return str(file_dict["prefix"])
        else:
            raise ValueError("No prefix found in file object in request.json")

    def get_files() -> dict:
        files_in_dict = {}
        file_name: str | None = None
        for k, v in file_dict.items():
            if k.startswith(prefix):
                file_name = file_dict["filename"] if file_name is None else file_name
                decoded_data = base64.b64decode(v)
                file_storage = FileStorage(stream=io.BytesIO(decoded_data))
                files_in_dict[file_name] = file_storage
        return files_in_dict

    json_payload = cast(list, request.json)
    files = {}
    session_id: str | None = None
    for file_dict in json_payload:
        session_id = file_dict["sessionId"] if session_id is None else session_id
        prefix: str = get_prefix()
        files = {**files, **get_files()}

    if session_id is None:
        raise ValueError("No session ID found in request.json")

    original_names_dict, full_document_dict = await sm_app.save_files_to_tmp(
        files, session_id=session_id
    )
    internal_file_id_mapping = await sm_app.save_files_to_vector_db(
        full_document_dict, user_id=session_id
    )
    time.sleep(1)
    external_file_id_mapping = [
        {"filename": original_names_dict[filename], "documentIds": document_ids}
        for filename, document_ids in internal_file_id_mapping.items()
    ]
    response_message = WEMUploadResponse(
        message=f"{str(len(files))} bestand{'en' if len(files) != 1 else ''} succesvol geüpload!",
        error="",
        fileIdMapping=external_file_id_mapping,
    )
    response = make_response(response_message, 200)
    return response


@app.route("/upload_files", methods=["POST"])
async def upload_files() -> Response:
    """
    Uploads files to the server.

    Returns:
        str: Success message indicating the number of files uploaded.
        tuple: Error message and status code if user is not authenticated.
    """
    session_id: str = str(get_property("sessionId"))

    def get_prefix() -> str:
        if "prefix" in request.form:
            return str(request.form["prefix"])
        else:
            raise ValueError("No prefix found in request.form or request.files")

    def get_files() -> dict:
        return {
            k.lstrip(prefix): v
            for k, v in request.files.items()
            if k.startswith(prefix)
        }

    prefix: str = get_prefix()
    files = get_files()

    original_names_dict, full_document_dict = await sm_app.save_files_to_tmp(
        files, session_id=session_id
    )
    internal_file_id_mapping = await sm_app.save_files_to_vector_db(
        full_document_dict, user_id=session_id
    )
    time.sleep(1)
    external_file_id_mapping = {
        original_names_dict[filename]: document_ids
        for filename, document_ids in internal_file_id_mapping.items()
    }
    response_message = UploadResponse(
        message=f"{str(len(files))} bestand{'en' if len(files) != 1 else ''} succesvol geüpload!",
        error="",
        fileIdMapping=external_file_id_mapping,
    )
    response = make_response(response_message, 200)
    return response


@app.route("/delete_file", methods=["DELETE"])
async def delete_file() -> Response:
    """
    Deletes a file from the server.

    Returns:
        str: Success message indicating the number of files deleted.
        tuple: Error message and status code if user is not authenticated.
    """
    session_id = str(get_property("sessionId"))
    file_name = str(get_property("filename"))
    document_ids = get_property("documentIds", property_type=list)
    deletion_successful = await sm_app.delete_docs_from_vector_db(
        document_ids, session_id=session_id
    )
    message, error = "", ""
    if deletion_successful:
        message = f"Bestand: {file_name} \n\n succesvol verwijderd!"
    else:
        error = f"Bestand: {file_name} \n\n niet gevonden!"
    response_message = ResponseMessage(message=message, error=error)
    response = make_response(response_message, 200 if deletion_successful else 400)
    return response


@app.route("/prompt", methods=["POST"])
def prompt() -> Response:
    """
    This function handles the prompt request from the client.

    Returns:
        tuple: A tuple containing the response message and the HTTP status code.
    """
    session_id = str(get_property("sessionId"))
    message = str(get_property("prompt"))
    chatbot = Chatbot(user_id=session_id)
    prompt_response = PromptResponse(
        message="Prompt result is found under the result key.",
        error="",
        result=chatbot.send_prompt(message),
    )
    return make_response(prompt_response, 200)


@app.route("/get_chat_history", methods=["GET"])
def get_chat_history() -> Response:
    """
    Gets the chat history.

    Returns:
        Response: A response object containing the chat history and status code.
    """
    session_id = str(get_property("sessionId"))
    memory_db = SQLChatMessageHistory(
        session_id, Utils.get_env_variable("CHAT_HISTORY_CONNECTION_STRING")
    )
    response_message = ChatHistoryResponse(
        message="Chatgeschiedenis succesvol opgehaald!",
        error="",
        result=messages_to_dict(memory_db.messages),
    )
    return make_response(response_message, 200)


@app.route("/clear_chat_history", methods=["DELETE"])
def clear_chat_history() -> Response:
    """
    Clears the chat history.

    Returns:
        Response: A response object containing the message and status code.
    """
    session_id = str(get_property("sessionId"))
    memory_db = SQLChatMessageHistory(
        session_id, Utils.get_env_variable("CHAT_HISTORY_CONNECTION_STRING")
    )
    memory_db.clear()
    response_message = ResponseMessage(
        message="Chatgeschiedenis succesvol gewist!", error=""
    )
    return make_response(response_message, 200)


@app.route("/submit_final_answer", methods=["POST"])
def submit_final_answer() -> Response:
    """
    This function handles the final answer submission from the client.

    Returns:
        tuple: A tuple containing the response message and the HTTP status code.
    """
    session_id = get_property("sessionId")
    original_answer = get_property("originalAnswer", property_type=dict)
    edited_answer = get_property("editedAnswer", property_type=dict)
    update_record_with_answers(
        session_id,
        original_answer=original_answer,
        edited_answer=edited_answer,
        logger=app.logger,
    )
    response_message = ResponseMessage(
        message="Final answer successfully submitted!", error=""
    )
    return make_response(response_message, 200)


if __name__ == "__main__":
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)
