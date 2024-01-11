import requests
from typing import Any
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile


Result = tuple[str, list[dict[str, str]], Any]

class Endpoints:
    @staticmethod
    def identify() -> dict[str, Any] | None:
        try:
            response = requests.get("http://127.0.0.1:5000/identify")
            json_response = response.json()
            if json_response["error"] != "":
                st.error(json_response["error"])
                return
            response_message = json_response["message"]
            st.toast(response_message, icon="🤗")
            return json_response
        except Exception as err:
            st.error(err, icon="❌")

    @staticmethod
    def upload_files(uploaded_files: list[UploadedFile], session_id: str | None = None) -> None:
        prefix = "file_"
        prefix_filename = lambda name: prefix + name
        files_with_prefix = {prefix_filename(file.name): (file.name, file.read(), file.type) for file in uploaded_files}
        prefix_entry = {"prefix": prefix}
        session_id_entry = {"sessionId": session_id} if session_id else {}
        form_data = {
            **prefix_entry,
              **session_id_entry,
                }
        try:
            response = requests.post("http://127.0.0.1:5000/upload_files", 
                                     data=form_data,
                                     files=files_with_prefix)
            json_response = response.json()
            if json_response["error"] != "":
                st.error(json_response["error"], icon="❌")
                return
            response_message = json_response["message"]
            st.toast(response_message, icon="✅")
        except Exception as err:
            st.error(err, icon="❌")

    @staticmethod
    def prompt(text_prompt: str) -> Result | None:
        try:
            response = requests.post("http://127.0.0.1:5000/prompt", data={"prompt": text_prompt})
            json_response = response.json()
            if json_response["error"] != "":
                st.error(json_response["error"], icon="❌")
                return None
            result = json_response["result"]
            citations = result["citations"]
            source_docs = result["source_documents"]
            answer = result["answer"]
            return answer, citations, source_docs
        except Exception as err:
            st.error(err)