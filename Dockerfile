# Pull Python 3.11.7 base image
FROM python:3.11.7

# Add arguments for api keys
ARG OPENAI_API_KEY
ARG HUGGINGFACE_API_KEY

# Add arguments for models
ARG CHAT_MODEL_VENDOR_NAME=openai
ARG CHAT_MODEL_NAME=gpt-turbo-3.5
ARG EMBEDDING_MODEL_VENDOR_NAME=openai
ARG EMBEDDING_MODEL_NAME=text-embedding-ada-002
ARG CHAT_HISTORY_CONNECTION_STRING=sqlite:///chat_history.db
ARG CHAT_MODEL_FOLDER_PATH
ARG EMBEDDING_MODEL_FOLDER_PATH

# Set working directory
WORKDIR /app

# Copy current contents of folder to app directory
COPY . /app

# Set cuBLAS environment variables
# ENV LLAMA_CUBLAS 1
# ENV CMAKE_ARGS "-DLLAMA_CUBLAS=on"

# Set Poetry environment variables
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=1.5.0
ENV PATH="$PATH:$POETRY_HOME/bin"

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set default environment variables
ENV CHAT_MODEL_VENDOR_NAME $CHAT_MODEL_VENDOR_NAME
ENV CHAT_MODEL_NAME $CHAT_MODEL_NAME
ENV EMBEDDING_MODEL_VENDOR_NAME $EMBEDDING_MODEL_VENDOR_NAME
ENV EMBEDDING_MODEL_NAME $EMBEDDING_MODEL_NAME
ENV OPENAI_API_KEY $OPENAI_API_KEY
ENV DORA_ENV DEV
ENV CHUNK_SIZE 512
ENV TOP_K_DOCUMENTS 5
ENV MINIMUM_ACCURACY 0.80
ENV FETCH_K_DOCUMENTS 100
ENV LAMBDA_MULT 0.2
ENV STRATEGY mmr
ENV CHAT_MODEL_FOLDER_PATH $CHAT_MODEL_FOLDER_PATH
ENV SENTENCE_TRANSFORMERS_HOME $EMBEDDING_MODEL_FOLDER_PATH

# Install necessary dependencies
RUN poetry config installer.max-workers 10
RUN poetry update -vvv --without dev

# Enable port 5000
EXPOSE 5000

# Execute Flask server on starting container
CMD ["poetry", "run", "flask", "--app", "server", "run"]
