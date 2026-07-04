from pathlib import Path

import pytest
import sqlalchemy

from chatdoc.utils import Utils
from server_modules.database import create_all_tables, get_engine, session_scope
from server_modules.models import (
    ChatHistoryBase,
    ChatHistoryModel,
    FinalAnswerBase,
    FinalAnswerModel,
)


@pytest.fixture(name="final_answer_connection_string")
def final_answer_connection_string_fixture(tmp_path: Path) -> str:
    db_path = tmp_path / "final_answer.db"
    connection_string = f"sqlite:///{db_path}"
    create_all_tables(FinalAnswerBase, connection_string)
    return connection_string


@pytest.fixture(name="chat_history_connection_string")
def chat_history_connection_string_fixture(tmp_path: Path) -> str:
    db_path = tmp_path / "chat_history.db"
    connection_string = f"sqlite:///{db_path}"
    create_all_tables(ChatHistoryBase, connection_string)
    return connection_string


@pytest.fixture(name="env_connection_strings")
def env_connection_strings_fixture(
    monkeypatch: pytest.MonkeyPatch,
    final_answer_connection_string: str,
    chat_history_connection_string: str,
) -> None:
    monkeypatch.setenv(
        "FINAL_ANSWER_CONNECTION_STRING", final_answer_connection_string
    )
    monkeypatch.setenv(
        "CHAT_HISTORY_CONNECTION_STRING", chat_history_connection_string
    )


def test_get_engine_is_cached(final_answer_connection_string: str) -> None:
    """
    get_engine should return the same (cached) Engine instance for the same
    connection string, to avoid creating a new connection pool every call.
    """
    first = get_engine(final_answer_connection_string)
    second = get_engine(final_answer_connection_string)
    assert first is second


def test_create_all_tables_is_idempotent(final_answer_connection_string: str) -> None:
    """
    Calling create_all_tables twice should not raise, and the table should exist.
    """
    create_all_tables(FinalAnswerModel, final_answer_connection_string)
    engine = get_engine(final_answer_connection_string)
    inspector = sqlalchemy.inspect(engine)
    assert "final_answer" in inspector.get_table_names()


def test_session_scope_commits_on_success(final_answer_connection_string: str) -> None:
    with session_scope(final_answer_connection_string) as session:
        session.execute(
            sqlalchemy.insert(FinalAnswerModel).values(session_id="abc")
        )

    with session_scope(final_answer_connection_string) as session:
        row = session.execute(
            sqlalchemy.select(FinalAnswerModel.__table__).where(
                FinalAnswerModel.session_id == "abc"
            )
        ).mappings().first()
    assert row is not None
    assert row["session_id"] == "abc"


def test_session_scope_rolls_back_on_error(final_answer_connection_string: str) -> None:
    with pytest.raises(ValueError):
        with session_scope(final_answer_connection_string) as session:
            session.execute(
                sqlalchemy.insert(FinalAnswerModel).values(session_id="rollback-me")
            )
            raise ValueError("boom")

    with session_scope(final_answer_connection_string) as session:
        row = session.execute(
            sqlalchemy.select(FinalAnswerModel.__table__).where(
                FinalAnswerModel.session_id == "rollback-me"
            )
        ).mappings().first()
    assert row is None


def test_chat_history_model_roundtrip(chat_history_connection_string: str) -> None:
    with session_scope(chat_history_connection_string) as session:
        session.execute(
            sqlalchemy.insert(ChatHistoryModel).values(
                session_id="sess-1", message={"role": "user", "content": "hi"}
            )
        )

    with session_scope(chat_history_connection_string) as session:
        rows = list(
            session.execute(sqlalchemy.select(ChatHistoryModel.__table__)).mappings()
        )
    assert len(rows) == 1
    assert rows[0]["session_id"] == "sess-1"
    assert rows[0]["message"] == {"role": "user", "content": "hi"}


def test_experiment_session_lifecycle(env_connection_strings: None) -> None:
    """
    Exercise ExperimentSessionMethods end-to-end against sqlite databases,
    covering add_new_session -> update_session -> retrieve_sessions /
    retrieve_chat_history, mirroring how server_modules.methods uses these
    functions in production.
    """
    from server_modules.methods import ExperimentSessionMethods

    session_id = "session-123"

    ExperimentSessionMethods.add_new_session(session_id)

    sessions = ExperimentSessionMethods.retrieve_sessions()
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == session_id
    assert sessions[0]["number_of_messages"] == -1

    with session_scope(
        Utils.get_env_variable("CHAT_HISTORY_CONNECTION_STRING")
    ) as session:
        session.execute(
            sqlalchemy.insert(ChatHistoryModel).values(
                session_id=session_id, message={"role": "user", "content": "hi"}
            )
        )
        session.execute(
            sqlalchemy.insert(ChatHistoryModel).values(
                session_id=session_id, message={"role": "assistant", "content": "hey"}
            )
        )

    ExperimentSessionMethods.update_session(
        session_id, {"original": True}, {"edited": True}
    )

    sessions = ExperimentSessionMethods.retrieve_sessions()
    assert len(sessions) == 1
    assert sessions[0]["number_of_messages"] == 2
    assert sessions[0]["original_answer"] == {"original": True}
    assert sessions[0]["edited_answer"] == {"edited": True}

    with pytest.raises(ValueError):
        ExperimentSessionMethods.update_session(
            "unknown-session", {}, {}
        )
