import requests
from typing import Any
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from streamlit_cookies_manager import CookieManager


Result = tuple[str, list[dict[str, str]], Any]


class Endpoints:
    @staticmethod
    def identify(cookie_manager: CookieManager, session_id: str | None = None) -> dict[str, Any] | None:
        try:
            session_id_entry = {"sessionId": session_id} if session_id else {}
            response = requests.get("http://127.0.0.1:5000/identify", data={**session_id_entry})
            json_response = response.json()
            if json_response["error"] != "":
                st.error(json_response["error"])
                return
            response_message = json_response["message"]
            cookie_manager["sessionId"] = json_response["sessionId"]
            st.toast(response_message, icon="🤗")
            return json_response
        except Exception as err:
            st.error(err, icon="❌")

    @staticmethod
    def upload_files(
        cookie_manager: CookieManager, uploaded_files: list[UploadedFile], session_id: str | None = None
    ) -> bool:
        if not cookie_manager.ready():
            st.stop()
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
            response = requests.post("http://127.0.0.1:5000/upload_files", data=form_data, files=files_with_prefix)
            json_response = response.json()
            if json_response["error"] != "":
                raise Exception(json_response["error"])
            response_message = json_response["message"]
            st.toast(response_message, icon="✅")
            return True
        except Exception as err:
            st.error(err, icon="❌")
        return False

    @staticmethod
    def prompt(cookie_manager: CookieManager, text_prompt: str, session_id: str | None = None) -> Result | None:
        if not cookie_manager.ready():
            st.stop()
        try:
            session_id_dict = {"sessionId": session_id} if session_id is not None else {}
            response = requests.post("http://127.0.0.1:5000/prompt", data={"prompt": text_prompt, **session_id_dict})
            json_response = response.json()
            if json_response["error"] != "":
                st.error(json_response["error"], icon="❌")
                return None
            result = json_response["result"]
            citations = result["citations"]["citations"]
            source_docs = result["source_documents"]
            answer = result["answer"]
            return answer, citations, source_docs
        except Exception as err:
            st.error(err)

    @staticmethod
    def clear_chat_history(cookie_manager: CookieManager, session_id: str | None = None) -> bool:
        if not cookie_manager.ready():
            st.stop()
        try:
            session_id_entry = {"sessionId": session_id} if session_id else {}
            response = requests.delete("http://127.0.0.1:5000/clear_chat_history", data={**session_id_entry})
            json_response = response.json()
            if json_response["error"] != "":
                raise Exception(json_response["error"])
            response_message = json_response["message"]
            st.toast(response_message, icon="✅")
            return True
        except Exception as err:
            st.error(err, icon="❌")
        return False
