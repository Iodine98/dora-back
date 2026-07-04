"""
Tests for the WebSocket transport added in `app_ws.py` (issue #62).

`app.py` (and by extension `app_ws.py`, which reuses its Flask `app`
instance) reads a couple of environment variables at import time
(`CURRENT_ENV`, `LOGGING_FILE_PATH`). These are set here, before the
`app`/`app_ws` modules are imported, so that importing them does not raise.
"""

import os
import tempfile

os.environ.setdefault("CURRENT_ENV", "TST")
os.environ.setdefault(
    "LOGGING_FILE_PATH", os.path.join(tempfile.gettempdir(), "dora-ws-test-logs", "dora-ws-test.log")
)

# pylint: disable=wrong-import-position
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

import app as app_module
from app_ws import app as flask_app
from app_ws import socketio


@pytest.fixture(name="socketio_client")
def fixture_socketio_client(monkeypatch):
    """
    Provides a `flask_socketio` test client connected to a session whose
    "file processing" future is already resolved, so that emitting a
    `prompt` event proceeds straight to invoking the (mocked) chatbot -
    mirroring how the HTTP `/prompt` endpoint behaves once uploads are done.

    A fresh, random session ID is used per test so that the shared
    `executor.futures` collection (a process-wide global) can never leak
    state between tests.
    """
    session_id = f"test-session-{uuid.uuid4()}"

    already_done_future = app_module.executor.submit(lambda: None)
    already_done_future.result()
    app_module.executor.futures.add(f"process_files_{session_id}", already_done_future)

    fake_chatbot = MagicMock()
    fake_chatbot.send_prompt = AsyncMock(return_value={"answer": "42", "chat_history": []})
    monkeypatch.setattr(app_module, "Chatbot", MagicMock(return_value=fake_chatbot))

    client = socketio.test_client(flask_app)
    try:
        yield client, session_id, fake_chatbot
    finally:
        client.disconnect()


def test_handle_prompt_emits_prompt_response(socketio_client):
    """
    A `prompt` event with a valid payload should be answered with a single
    `prompt_response` event whose payload mirrors the HTTP `/prompt`
    endpoint's JSON body, built from the shared `resolve_prompt_response`
    business logic.
    """
    client, session_id, fake_chatbot = socketio_client

    client.emit("prompt", {"sessionId": session_id, "prompt": "What is the answer?"})
    received = client.get_received()

    assert len(received) == 1
    event = received[0]
    assert event["name"] == "prompt_response"

    payload = event["args"][0]
    assert payload["error"] == ""
    assert payload["result"] == {"answer": "42", "chat_history": []}
    fake_chatbot.send_prompt.assert_called_once_with("What is the answer?")


def test_handle_prompt_emits_error_on_malformed_payload(socketio_client):
    """
    A `prompt` event missing the required `prompt` key should not raise
    inside the handler; instead an error should be reported back to the
    client via a `prompt_response` event.
    """
    client, session_id, fake_chatbot = socketio_client

    client.emit("prompt", {"sessionId": session_id})
    received = client.get_received()

    assert len(received) == 1
    payload = received[0]["args"][0]
    assert payload["message"] == ""
    assert payload["error"]
    fake_chatbot.send_prompt.assert_not_called()
