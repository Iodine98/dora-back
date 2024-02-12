## Pull builder image
FROM python:3.11.7 as builder

# Set working directory
WORKDIR /app

# Copy poetry.lock and pyproject.toml
COPY pyproject.toml /app/

# Set Poetry environment variables
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=1.5.0 \
    POETRY_CACHE_DIR="/tmp/poetry_cache"
ENV PATH="$PATH:$POETRY_HOME/bin"

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Install necessary dependencies
RUN poetry config installer.max-workers 10
RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install -vvv --without dev --no-root

#-----------------------------------------------------------------------------------

## Runtime Image
FROM  python:3.11.7 as runtime

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


# Copy current contents of folder to app directory
COPY . /app

# Enable port 5000
EXPOSE 5000

# Execute Flask server on starting container
ENTRYPOINT ["flask", "--app", "server", "run", "--host=0.0.0.0"]
