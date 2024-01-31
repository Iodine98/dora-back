# dora-back
The backend for Dora

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
- `CURRENT_ENV`: the current environment [DEV, TST, PROD]
- `CHAT_MODEL_FOLDER_PATH`: the path to the folder of local chat models
- `EMBEDDING_MODEL_FOLDER_PATH`: the path to the folder of local embedding models

Then run `poetry run flask --app server run`

### Run the Streamlit app

Run `poetry run streamlit st_app.py` 

## Run Flask server using Docker container

Please configure the values in the Dockerfile before proceeding.

Build the Docker container using 
```bash
docker build -t dora-back --build-args OPENAI_API_KEY=<openai_api_key> .
```
The `--build-args` are needed to provide options for local models or API keys.

Run the Docker container using:
```bash
docker run --name <container_name> -p 5000:5000 dora-back \
-e <environment_variable>=<value> \
-e <environment_variable>=<value>
```
You can access the server at localhost:5000.
Overriding the default values for the environment variables is optional.


