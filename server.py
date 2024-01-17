# system imports
import uuid
import os
import json
from typing import Any, cast


import logging

# third party imports
from flask import Flask, request, session, make_response, Response

from flask_cors import CORS

# local imports
from serf.methods import ServerMethods
from serf.class_defs import IdentifyResponse, Identity, ResponseMessage, PromptResponse, UploadResponse
from chatdoc.chatbot import Chatbot


app = Flask(__name__)
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True

current_env = os.environ.get("CURRENT_ENV", "DEV")

list_of_allowed_origins: list[str] = []
app.logger.setLevel(logging.INFO)
match current_env:
    case "DEV":
        CORS(app)
        if os.environ.get("DEV_URL") is not None:
            list_of_allowed_origins.append(os.environ["DEV_URL"])
        else:
            raise ValueError("DEV_URL environment variable not set")
        app.logger.log(level=logging.INFO, msg="Running in development mode")
    case "PROD":
        app.logger.log(level=logging.INFO, msg="Running in production mode")
    case _:
        raise ValueError("Invalid environment variable set for CURRENT_ENV")

app.secret_key = str(uuid.uuid4())
sm_app = ServerMethods(app)

Basic = str | int | float | bool
Property = Basic | dict | tuple | list


def get_property(property_name: str, with_error=True, property_type: type[Property] = str) -> Any:
    """
    Gets a property from the request object.

    Args:
        property_name (str): The name of the property to get from the request object.

    Raises:
        ValueError: If the property is not found in the request object.

    Returns:
        str: The property value.
    """
    property_value: str
    if property_name in session:
        property_value = session[property_name]
    elif property_name in request.form:
        property_value = request.form[property_name]
    elif with_error:
        raise ValueError(f"No {property_name} found in request.form or session")
    else:
        return cast(property_type, None)
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
            response_message = ResponseMessage(message="", error="No origin header found")
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


@app.route("/identify", methods=["GET"])
def identify() -> Response:
    """
    Identifies the user and returns a response object.

    Returns:
        dict: A response object containing the sessionId and message.
    """
    if (session_id := get_property("sessionId", with_error=False)) and isinstance(session_id, str):
        identity = Identity(
            sessionId=session_id,
            authenticated=True,
            hasDB=bool(get_property("hasDB", with_error=False, property_type=bool)),
        )
        identify_response = IdentifyResponse(message=f"Welcome back user: {session_id} !", error="", **identity)
    else:
        identity = Identity(sessionId=str(uuid.uuid4()), authenticated=True, hasDB=False)
        identify_response = IdentifyResponse(
            message=f"Welcome new user: {identity['sessionId']} !", error="", **identity
        )

    session.update(identity)
    response = make_response(identify_response, 200)
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
        return {k.lstrip(prefix): v for k, v in request.files.items() if k.startswith(prefix)}

    prefix: str = get_prefix()
    files = get_files()

    original_names_dict, full_document_dict = await sm_app.save_files_to_tmp(files, session_id=session_id)
    internal_file_id_mapping = await sm_app.save_files_to_vector_db(full_document_dict, user_id=session_id)
    external_file_id_mapping = {
        original_names_dict[filename]: document_ids for filename, document_ids in internal_file_id_mapping.items()
    }
    response_message = UploadResponse(
        message=f"{str(len(files))} file{'s' if len(files) != 1 else ''} uploaded successfully!",
        error="",
        file_id_mapping=external_file_id_mapping,
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
    deletion_successful = sm_app.delete_docs_from_vector_db(document_ids, session_id=session_id)
    message, error = "", ""
    if deletion_successful:
        message = f"File {file_name} deleted successfully!"
    else:
        error = f"File {file_name} not found!"
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
    if request.form is None:
        return make_response({"error": "No form data received"}, 400)
    message = request.form["prompt"]
    chatbot = Chatbot(user_id=session_id)
    prompt_response = PromptResponse(
        message="Prompt result is found under the result key.", error="", result=chatbot.send_prompt(message)
    )
    return make_response(prompt_response, 200)


if __name__ == "__main__":
    app.run(port=5000)
