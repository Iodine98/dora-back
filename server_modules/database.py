"""
Shared SQLAlchemy 2.0 engine/session utilities.

This module centralizes engine creation and session handling so that the
rest of the codebase (e.g. ``server_modules.methods``) does not need to
repeat ``sqlalchemy.create_engine(...)`` boilerplate for every database
operation. Engines are cached per connection string so repeated calls reuse
the same connection pool.
"""

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

import sqlalchemy
from sqlalchemy import Engine
from sqlalchemy.orm import DeclarativeBase, Session


@lru_cache(maxsize=None)
def get_engine(connection_string: str) -> Engine:
    """
    Get a (cached) SQLAlchemy engine for the given connection string.

    Engines are expensive to create and are meant to be reused, so this
    function caches one engine per unique connection string.
    """
    return sqlalchemy.create_engine(connection_string)


def create_all_tables(base: type[DeclarativeBase], connection_string: str) -> None:
    """
    Create all tables belonging to ``base``'s metadata if they don't exist yet.
    """
    engine = get_engine(connection_string)
    base.metadata.create_all(engine)


@contextmanager
def session_scope(connection_string: str) -> Iterator[Session]:
    """
    Provide a transactional session scope bound to the engine for
    ``connection_string``.

    On successful exit the transaction is committed; on exception it is
    rolled back. The session is always closed.
    """
    session = Session(get_engine(connection_string))
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
