## Pull builder image
FROM python:3.11.7 AS builder

# Set working directory
WORKDIR /app

# Set Poetry environment variables
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=1.5.0 \
    POETRY_CACHE_DIR="/tmp/poetry_cache"
ENV PATH="$PATH:$POETRY_HOME/bin"

# Install MariaDB Connector/C dev headers so the `mariadb` package can be built
# from source (PyPI only ships Windows wheels for it; on Linux, pip/poetry
# always builds it from the sdist, which needs `mariadb_config` on PATH at
# build time).
# NOTE: we deliberately run the repo-setup + install directly in this stage
# instead of copying apt sources state from a separate stage: the
# `mariadb_repo_setup` script's output file name/format (one-line `.list` vs.
# deb822 `.sources`) is an undocumented implementation detail that has changed
# upstream, which makes cross-stage COPY of that file fragile.
#
# This runs before `COPY pyproject.toml` (further down) so that this layer -
# which never changes on its own - stays cached across the frequent
# dependency bumps in pyproject.toml, instead of being invalidated by them.
# Since this no longer depends on anything from the runtime stage (and vice
# versa), BuildKit can run both stages' apt-get RUNs concurrently; they use
# `sharing=locked` on the shared /var/cache/apt mount so BuildKit serializes
# access instead of both processes racing for apt's own internal lock file.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked apt-get update && apt-get install -y wget gnupg \
    && wget https://r.mariadb.com/downloads/mariadb_repo_setup \
    && chmod +x mariadb_repo_setup \
    && ./mariadb_repo_setup --mariadb-server-version="mariadb-10.11.18" \
    && apt-get update && apt-get install -y libmariadb3 libmariadb-dev \
    && rm -f mariadb_repo_setup

# Install Poetry
RUN pip install poetry

RUN poetry config installer.max-workers 10

# Copy poetry.lock and pyproject.toml
COPY pyproject.toml /app/

# Install necessary dependencies
RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install -v --no-root

#-----------------------------------------------------------------------------------

## Runtime Image
# Uses the slim variant here (unlike the builder stage) since this stage
# only runs the already-built venv/app code - it never compiles anything
# (mariadb/llama-cpp-python are only built from source in the builder
# stage), so it doesn't need the extra build tooling the full python image
# carries. This meaningfully shrinks the final image (and therefore the
# image-export/GHA-cache-upload time that dominates docker-integration CI -
# see the discussion on #85/#86).
FROM python:3.11-slim AS runtime

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Add arguments for api keys
# ARG OPENAI_API_KEY
# ARG HUGGINGFACE_API_KEY

# # Add arguments for models
# ARG CHAT_MODEL_VENDOR_NAME=openai
# ARG CHAT_MODEL_NAME=gpt-3.5-turbo
# ARG EMBEDDING_MODEL_VENDOR_NAME=openai
# ARG EMBEDDING_MODEL_NAME=text-embedding-ada-002
# ARG CHAT_HISTORY_CONNECTION_STRING=sqlite:///chat_history.db
# ARG FINAL_ANSWER_CONNECTION_STRING=sqlite:///final_answer.db
# ARG CHAT_MODEL_FOLDER_PATH
# ARG EMBEDDING_MODEL_FOLDER_PATH

# # Set default environment variables
# ENV CHAT_MODEL_VENDOR_NAME $CHAT_MODEL_VENDOR_NAME
# ENV CHAT_MODEL_NAME $CHAT_MODEL_NAME
# ENV EMBEDDING_MODEL_VENDOR_NAME $EMBEDDING_MODEL_VENDOR_NAME
# ENV EMBEDDING_MODEL_NAME $EMBEDDING_MODEL_NAME
# ENV OPENAI_API_KEY $OPENAI_API_KEY
# ENV CURRENT_ENV DEV
# ENV CHUNK_SIZE 512
# ENV CHUNK_OVERLAP 0
# ENV TOP_K_DOCUMENTS 5
# ENV MINIMUM_ACCURACY 0.80
# ENV FETCH_K_DOCUMENTS 100
# ENV LAMBDA_MULT 0.2
# ENV STRATEGY mmr
# ENV LAST_N_MESSAGES 5
# ENV CHAT_MODEL_FOLDER_PATH $CHAT_MODEL_FOLDER_PATH
ENV SENTENCE_TRANSFORMERS_HOME=$EMBEDDING_MODEL_FOLDER_PATH
# ENV CHAT_HISTORY_CONNECTION_STRING $CHAT_HISTORY_CONNECTION_STRING
# ENV FINAL_ANSWER_CONNECTION_STRING $FINAL_ANSWER_CONNECTION_STRING
# ENV LOGGING_FILE_PATH /app/logs/dora-backend.log


# Set virtual environment and Path
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Install MariaDB Connector/C runtime library.
# We run the full repo-setup + install here (rather than COPYing apt sources
# state from another stage) because `mariadb_repo_setup`'s output file
# name/format is an undocumented, unstable detail of the upstream script (it
# has switched between the one-line `.list` format and the deb822 `.sources`
# format), and copying that file between stages breaks silently when it
# changes. Only the shared library is needed at runtime (not the -dev
# headers, which are only required when building the `mariadb` wheel in the
# builder stage above).
#
# This runs before `COPY --from=builder`/`COPY . /app` (further down) so that
# this layer - which never changes on its own - stays cached across builds,
# instead of being invalidated every time the venv or source changes. Since
# this no longer depends on the builder stage, BuildKit can run both stages'
# apt-get RUNs concurrently; they use `sharing=locked` on the shared
# /var/cache/apt mount so BuildKit serializes access instead of both
# processes racing for apt's own internal lock file.
#
# `curl` is included because `mariadb_repo_setup` itself checks for it as a
# prerequisite - the full python image happens to have it preinstalled, but
# python:3.11-slim (used for this stage) doesn't.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked apt-get update && apt-get install -y wget gnupg curl \
    && wget https://r.mariadb.com/downloads/mariadb_repo_setup \
    && chmod +x mariadb_repo_setup \
    && ./mariadb_repo_setup --mariadb-server-version="mariadb-10.11.18" \
    && apt-get update && apt-get install -y libmariadb3 \
    && rm -f mariadb_repo_setup

# Copy the virtual environment from the builder
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

# Copy current contents of folder to app directory
COPY . /app

# Enable port 8000 
EXPOSE 8000

# Enable debug port
EXPOSE 5678

# Execute Flask server on starting container.
#
# `app_ws:app` is the same Flask `app` object as `app:app`, with a
# flask-socketio WebSocket layer attached on top (see app_ws.py). Real-time
# WebSocket support under a WSGI stack like Flask requires a cooperative
# worker class - `geventwebsocket.gunicorn.workers.GeventWebSocketWorker` -
# rather than the default sync worker, so `--threads`/gthread is dropped, and
# only a single worker (`-w 1`) is used since Flask-SocketIO needs clients
# stuck to the same worker process (see app_ws.py for the full rationale,
# including why this uses gevent instead of eventlet, and why it does NOT use
# `uvicorn` - an ASGI server - as originally suggested in issue #62).
CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "-w", "1", "--preload", "-b", "0.0.0.0:8000", "--timeout", "600", "app_ws:app"]
