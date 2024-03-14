## Pull builder image
FROM python:3.11.7 as builder

# Set working directory
WORKDIR /app

# Copy poetry.lock and pyproject.toml
COPY pyproject.toml /app/

ARG HTTP_PROXY
ARG HTTPS_PROXY

# Set Poetry environment variables
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=1.5.0 \
    POETRY_CACHE_DIR="/tmp/poetry_cache"
ENV PATH="$PATH:$POETRY_HOME/bin"
ENV HTTP_PROXY=$HTTP_PROXY

# Install Poetry
RUN pip config set global.proxy ${HTTP_PROXY}
RUN pip install poetry

# Install necessary dependencies
RUN poetry config installer.max-workers 10
RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install -vvv --without dev --no-root

#-----------------------------------------------------------------------------------
## Install MariaDB Connector/C

FROM ubuntu:22.04 as mariadb-connector-c


RUN --mount=type=cache,target=/var/cache/apt apt-get update && apt-get install -y wget curl gnupg
RUN wget https://r.mariadb.com/downloads/mariadb_repo_setup
RUN chmod +x mariadb_repo_setup
RUN ./mariadb_repo_setup --mariadb-server-version="mariadb-10.6"
RUN --mount=type=cache,target=/var/cache/apt apt-get update && apt-get install -y libmariadb3 libmariadb-dev

#-----------------------------------------------------------------------------------

## Runtime Image
FROM  python:3.11.7 as runtime

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Add arguments for api keys
ARG OPENAI_API_KEY
ARG HUGGINGFACE_API_KEY

# Add arguments for models
ARG CHAT_MODEL_VENDOR_NAME=openai
ARG CHAT_MODEL_NAME=gpt-3.5-turbo
ARG EMBEDDING_MODEL_VENDOR_NAME=openai
ARG EMBEDDING_MODEL_NAME=text-embedding-ada-002
ARG CHAT_HISTORY_CONNECTION_STRING=sqlite:///chat_history.db
ARG FINAL_ANSWER_CONNECTION_STRING=sqlite:///final_answer.db
ARG CHAT_MODEL_FOLDER_PATH
ARG EMBEDDING_MODEL_FOLDER_PATH

# Set default environment variables
ENV CHAT_MODEL_VENDOR_NAME $CHAT_MODEL_VENDOR_NAME
ENV CHAT_MODEL_NAME $CHAT_MODEL_NAME
ENV EMBEDDING_MODEL_VENDOR_NAME $EMBEDDING_MODEL_VENDOR_NAME
ENV EMBEDDING_MODEL_NAME $EMBEDDING_MODEL_NAME
ENV OPENAI_API_KEY $OPENAI_API_KEY
ENV CURRENT_ENV DEV
ENV CHUNK_SIZE 512
ENV CHUNK_OVERLAP 0
ENV TOP_K_DOCUMENTS 5
ENV MINIMUM_ACCURACY 0.80
ENV FETCH_K_DOCUMENTS 100
ENV LAMBDA_MULT 0.2
ENV STRATEGY mmr
ENV LAST_N_MESSAGES 5
ENV CHAT_MODEL_FOLDER_PATH $CHAT_MODEL_FOLDER_PATH
ENV SENTENCE_TRANSFORMERS_HOME $EMBEDDING_MODEL_FOLDER_PATH
ENV CHAT_HISTORY_CONNECTION_STRING $CHAT_HISTORY_CONNECTION_STRING
ENV FINAL_ANSWER_CONNECTION_STRING $FINAL_ANSWER_CONNECTION_STRING
ENV LOGGING_FILE_PATH /app/logs/dora-backend.log


# Set virtual environment and Path
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Copy the virtual environment from the builder
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

# # Copy MariaDB Connector/C
COPY --from=mariadb-connector-c /etc/apt/sources.list.d/mariadb.list /etc/apt/sources.list.d/mariadb.list



# Copy current contents of folder to app directory
COPY . /app

# Enable port 8000 
EXPOSE 8000

# Execute Flask server on starting container
CMD ["gunicorn", "-w", "2", "--threads", "2", "-b", "0.0.0.0:8000", "app:app"]
