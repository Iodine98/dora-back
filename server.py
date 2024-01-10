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
    origin = request.headers.get("Origin")
    if origin is None:
        response_message = ResponseMessage(message="", error="No origin header found")
        return make_response(response_message, 400)
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
    identity = Identity(sessionId=str(uuid.uuid4()), authenticated=True, hasDB=False)
    identify_response = IdentifyResponse(message=f"Welcome new user: {identity['sessionId']} !", error="", **identity)
    if "sessionId" in session and isinstance(session["sessionId"], str):
        identity = Identity(sessionId=session["sessionId"], authenticated=True, hasDB=session["hasDB"])
        identify_response = IdentifyResponse(
            message=f"Welcome back user: {session['sessionId']} !", error="", **identity
        )
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

    if "sessionId" not in session:
        return make_response({"error": "You have not been authenticated, please identify yourself first."}, 401)
    prefix: str = request.form["prefix"]
    files = {k.lstrip(prefix): v for k, v in request.files.items() if k.startswith(prefix)}
    full_document_dict = sm_app.save_files(files, session["sessionId"])
    loop = asyncio.new_event_loop()
    loop.run_until_complete(sm_app.process_files(full_document_dict, session["sessionId"]))
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
    if "sessionId" not in session:
        return make_response({"error": "You have not been authenticated, please identify yourself first."}, 401)
    if request.form is None:
        return make_response({"error": "No form data received"}, 400)
    message = request.form["prompt"]
    chatbot = Chatbot(
        user_id=session["sessionId"],
        document_dict=session["files"],
    )
    prompt_response = PromptResponse(
        message="Prompt result is found under the result key.", error="", result=chatbot.send_prompt(message)
    )
    return make_response(prompt_response, 200)


if __name__ == "__main__":
    app.run()
