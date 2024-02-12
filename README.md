# dora-back
The backend for Dora

For deployment at SBP: please have a look at the [README.md](https://github.com/Iodine98/dora-streamlit#dora-streamlit) on `dora-streamlit`. Deploy this project in two different environments: one where the `dora-backend` service is based on the `main` branch and another where the `dora-backend` service is based on the `research-experiment` branch.

## Run using Poetry and Python

### How to install the dependencies
Either clone this project in VSCode or open a new codespace (if you have not been invited into another one).

The `devcontainer.json` should contain all the plugins needed to get going including the installation of Poetry (which may need to be done manually).

Additionally, set the `FILE_PATH` environment variable to where you store the PDF file and include your OpenAI API key in the `OPENAI_API_KEY` environment variable.

Subsequently, run `poetry update` in the terminal to install all the dependencies and create the environment. 

### Allow GPU-inference for local models

Set the `CMAKE_ARGS` environment variable according to the [llama-cpp-python documentation](https://pypi.org/project/llama-cpp-python)

### Run the Flask server for the endpoints

Make sure to set all the environment variables like:

- `CHAT_MODEL_VENDOR_NAME`: the name of the chat model vendor [openai, local, huggingface]
- `CHAT_MODEL_NAME`: the name of the chat model (e.g. gpt-turbo-3.5)
- `EMBEDDING_MODEL_VENDOR_NAME`: the name of the embeddings model vendor [openai, local, huggingface]
- `EMBEDDING_MODEL_NAME`: the name of the embeddings model (e.g. text-embedding-ada-002)
- `CURRENT_ENV`: the current environment [DEV, TST, PROD]. In `DEV` a CORS wrapper is applied to the Flask-server, but not in `TST` or `PROD`. In `PROD`, the server will connect to a defined remote endpoint for the Chroma Vector DB, but in `DEV` and `TST`, it will make use of a persistent client in Python.
- `CHAT_MODEL_FOLDER_PATH`: the path to the folder of local chat models
- `EMBEDDING_MODEL_FOLDER_PATH`: the path to the folder of local embedding models
- `OPENAI_API_KEY`: an OpenAI API key to use an OpenAI model specified in `CHAT_MODEL_NAME`
- `CURRENT_ENV`: the current environment for the Flask server; defaults to `DEV`
- `CHUNK_SIZE`: the chunk size in which to partition the chunks from the text extracted from documents; defaults to `512` tokens.
- `TOP_K_DOCUMENTS`: retrieve the top-k documents; defaults to the top-`5` documents.
- `MINIMUM_ACCURACY`: the minimum accuracy for the retrieved documents (i.e. chunks of text); defaults to `0.80`
- `FETCH_K_DOCUMENTS`: fetch `k`-number of documents (only applies if `STRATEGY=mmr`); defaults to `100`
- `LAMBDA_MULT`: Lambda-multiplier, the lower this number (between 0 and 1) the more diverse the documents ought to be, the higher the less diverse the document selection is; defaults to `0.2`
- `STRATEGY`: the document ranking strategy to use; for example `similarity`, `similarity_score_threshold` or `mmr` (default)
- `LAST_N_MESSAGES`: the last n messages to include from the chat history; defaults to `5`.
- `CHAT_MODEL_FOLDER_PATH`: the folder path to store LOCAL chat models in.
- `SENTENCE_TRANSFORMERS_HOME`: the folder path to store LOCAL embedding models in.
- `CHAT_HISTORY_CONNECTION_STRING`: an SQL-connection string pointing towards a SQL-DB where chat history can be stored in. The schema will automatically be created in the database mentioned in the SQL-connection string

Then run `poetry run flask --app server run`

### Run the Streamlit app

Run `poetry run streamlit st_app.py` 

## Run Flask server using Docker container

Please configure the values in the Dockerfile before proceeding.

Build the Docker container using 
```bash
docker build -t dora-backend --build-arg OPENAI_API_KEY=<openai_api_key> .
```
The `--build-arg` are needed to provide options for local models or API keys. **Please have a look at the Dockerfile** to familiarize yourself with any defaults.

Run the Docker container using:
```bash
docker run --name <container_name> -p 5000:5000 dora-back \
-e <environment_variable>=<value> \
-e <environment_variable>=<value>
```
You can access the server at localhost:5000.
Overriding the default values for the environment variables is optional.

## Removing CORS and connecting to remote Vector DB
To be able to remove the CORS wrapper and connect to a remote vector database, set the `CURRENT_ENV` variable to `PROD`.

