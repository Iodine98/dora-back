"""
WebSocket transport for the DoRA backend (issue #62).

This module attaches a `flask_socketio.SocketIO` layer to the very same Flask
application object defined in `app.py`, instead of duplicating the whole
Flask app (routes, Swagger config, CORS/OPTIONS handling, error handler,
executor, etc.). All HTTP routes defined in `app.py` keep working exactly as
before; this module only adds a `prompt` WebSocket event as an alternative,
bidirectional transport for the same use case that the HTTP `POST /prompt`
endpoint serves.

The actual business logic (looking up whether uploaded files are still being
processed, invoking the `Chatbot`, shaping the response payload) lives in
`app.resolve_prompt_response` and is shared by both transports, so it is not
duplicated here.

## A note on "uvicorn" (see issue #62)

The original issue asked to "Add uvicorn as a service to the Dockerfile".
That does not actually apply to this stack:

- `uvicorn` is an **ASGI** server (it runs `async def app(scope, receive,
  send)`-style applications, e.g. Starlette/FastAPI, or ASGI-wrapped WSGI
  apps).
- Flask (and `flask-socketio` on top of it) is a **WSGI** application.
  `flask-socketio` achieves real-time, bidirectional WebSocket support on top
  of a WSGI stack by using a cooperatively-scheduled worker (`eventlet` or
  `gevent`) that can hold a connection open and still service other
  greenlets/requests concurrently. `gunicorn` is told to use that worker via
  a dedicated worker class, not by swapping in an ASGI server.
- Running this Flask app under `uvicorn` directly would require wrapping it
  with an ASGI adapter (e.g. `asgiref.wsgi.WsgiToAsgi`) and would *not* give
  WebSocket support for free — `flask-socketio`'s WebSocket transport
  specifically depends on the `eventlet`/`gevent` monkey-patching model, not
  on ASGI.

Given that, this change adds `gevent` + `gevent-websocket` (not `uvicorn`) as
the async worker dependencies. `eventlet` was considered first (it is the
worker most older Flask-SocketIO tutorials reach for), but as of 2024/2025
`eventlet` is in maintenance-only "life support" mode with stalled feature
development, so `gevent` — which is still actively maintained and is the
option Flask-SocketIO's own docs currently steer new deployments towards —
was chosen instead. The Dockerfile's gunicorn command now uses
`-k geventwebsocket.gunicorn.workers.GeventWebSocketWorker` and serves
`app_ws:app` (the same Flask `app` object, now with the SocketIO layer
attached) so that both the existing HTTP routes and the new WebSocket
endpoint are served from a single process/port. This is documented in the PR
description as a deliberate deviation from the issue's literal wording.

## A note on worker count

Gunicorn is run with a single worker (`-w 1`) here. Flask-SocketIO relies on
clients keeping a sticky connection to the same worker process for the
lifetime of a session; gunicorn's built-in load balancing does not guarantee
that, so with more than one worker some clients would fail to connect. Scaling
to multiple workers/nodes requires a shared message queue (e.g. Redis) so
that SocketIO instances across processes can coordinate broadcasts - that is
out of scope for this change and left as a future improvement if/when
horizontal scaling of the WebSocket endpoint is needed.
"""

import asyncio
from typing import Any

from flask_socketio import SocketIO, emit

from app import app, resolve_prompt_response

# `async_mode="gevent"` makes flask-socketio use gevent's cooperative
# scheduler so that long-lived WebSocket connections don't block the worker
# from handling other clients. See the module docstring above for why this
# is `gevent` rather than `eventlet` or `uvicorn`/ASGI.
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")


@socketio.on("prompt")
def handle_prompt(data: dict[str, Any]) -> None:
    """
    Handles the prompt request from the client via WebSocket.

    Mirrors the behaviour of the HTTP `POST /prompt` endpoint defined in
    `app.py`, reusing the same `resolve_prompt_response` business logic.
    Emits a `prompt_response` event back to the requesting client with the
    same payload shape (`message`, `error`, and on success `result`) that the
    HTTP endpoint returns as its JSON body.

    Args:
        data (dict): The payload sent by the client, expected to contain a
            `sessionId` and a `prompt` key.
    """
    try:
        session_id = str(data["sessionId"])
        message = str(data["prompt"])
        response_message, _status_code = asyncio.run(
            resolve_prompt_response(session_id, message)
        )
        emit("prompt_response", response_message)
    except Exception as error:  # pylint: disable=broad-except
        emit("prompt_response", {"message": "", "error": str(error)})


if __name__ == "__main__":
    # Local/dev entrypoint. In production, gunicorn with the eventlet worker
    # class serves `app_ws:app` directly (see Dockerfile), so this branch is
    # not exercised in the container.
    socketio.run(app, host="0.0.0.0", port=5000)
