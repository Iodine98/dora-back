# system imports
import uuid
import os
import asyncio


import logging

# third party imports
from flask import Flask, request, session, make_response, Response

from flask_cors import CORS

# local imports
from serf.methods import ServerMethods
from serf.class_defs import IdentifyResponse, Identity, ResponseMessage, PromptResponse
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

def get_property(property_name: str, with_error=True) -> str | None:
    """
    Gets a property from the request object.

    Args:
        property_name (str): The name of the property to get from the request object.

    Raises:
        ValueError: If the property is not found in the request object.

    Returns:
        str: The property value.
    """
    if property_name in session:
        return str(session[property_name])
    elif property_name in request.form:
        return str(request.form[property_name])
    else:
        if with_error:
            raise ValueError(f"No {property_name} found in request.form or session")
        return None


@app.errorhandler(ValueError)  # type: ignore
def handle_value_error(error: ValueError) -> Response:
    """
    Handles a ValueError.

    Args:
        error (ValueError): The ValueError to handle.

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
        identity = Identity(sessionId=session_id, authenticated=True, hasDB=bool(get_property("hasDB", with_error=False)))
        identify_response = IdentifyResponse(
            message=f"Welcome back user: {session_id} !", error="", **identity
        )
    else:
        identity = Identity(sessionId=str(uuid.uuid4()), authenticated=True, hasDB=False)
        identify_response = IdentifyResponse(message=f"Welcome new user: {identity['sessionId']} !", error="", **identity)
    
    session.update(identity)
    response = make_response(identify_response, 200)
    return response




@app.route("/upload_files", methods=["POST"])
def upload_files() -> Response:
    """
    Uploads files to the server.

    Returns:
        str: Success message indicating the number of files uploaded.
        tuple: Error message and status code if user is not authenticated.
    """

    def get_prefix() -> str:
        if "prefix" in request.form:
            return str(request.form["prefix"])
        else:
            raise ValueError("No prefix found in request.form or request.files")

    def get_files() -> dict:
        return  {k.lstrip(prefix): v for k, v in request.files.items() if k.startswith(prefix)}

    session_id: str = str(get_property("sessionId"))
    prefix: str = get_prefix()
    files = get_files()
    full_document_dict = sm_app.save_files(files, session_id=session_id)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(sm_app.process_files(full_document_dict, user_id=session_id))
    loop.close()
    session["files"] = {file_name: str(file_path) for file_name, file_path in full_document_dict.items()}
    response_message = ResponseMessage(
        message=f"{str(len(files))} file{'s' if len(files) != 1 else ''} uploaded successfully!", error=""
    )
    response = make_response(response_message, 200)
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
    chatbot = Chatbot(
        user_id=session_id,
        # document_dict=session["files"],
    )
    prompt_response = PromptResponse(
        message="Prompt result is found under the result key.", error="", result=chatbot.send_prompt(message)
    )
    return make_response(prompt_response, 200)


if __name__ == "__main__":
    app.run(port=5000)
