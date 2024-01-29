# Using Docker image that corresponds to a stable Debian distro with Python 3.11.7
FROM python:3.11.7-bullseye

# Add argument OPENAI_API_KEY
ARG OPENAI_API_KEY

# Set working directory
WORKDIR /app

# Copy current contents of folder to app directory
ADD . /app

# Set cuBLAS environment variables
ENV LLAMA_CUBLAS 1
ENV CMAKE_ARGS "-DLLAMA_CUBLAS=on"

# Set Poetry environment variables
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=1.5.0
ENV PATH="$PATH:$POETRY_HOME/bin"

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set default environment variables
ENV CHAT_MODEL_VENDOR_NAME openai
ENV CHAT_MODEL_NAME gpt-turbo-3.5
ENV EMBEDDING_MODEL_VENDOR_NAME openai
ENV EMBEDDING_MODEL_NAME text-embedding-ada-002
ENV OPENAI_API_KEY $OPENAI_API_KEY
ENV DORA_ENV DEV

# Install necessary dependencies
RUN poetry config installer.max-workers 10
RUN poetry update -vv --without dev

# Enable port 5000
EXPOSE 5000

# Execute Flask server on starting container
CMD ["poetry", "run", "flask", "--app", "server", "run"]
