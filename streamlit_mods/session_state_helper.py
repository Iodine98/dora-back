from typing import Any
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from streamlit_mods.endpoints import Endpoints

from streamlit_cookies_manager import CookieManager

class MessageHelper:
    def __init__(self, cookie_manager: CookieManager) -> None:
        self.cookie_manager = cookie_manager
        st.session_state.messages = self.messages
        st.session_state.is_clear = self.is_clear

    @property
    def messages(self) -> list:
        if "messages" in st.session_state:
            return st.session_state.messages
        return []
    
    def get_last_message(self) -> dict[str, Any] | None:
        if len(st.session_state.messages) == 0:
            return None
        return st.session_state.messages[-1]

    def add_bot_message(self, content: str, citations: list[dict[str, str]], sources: Any, time: float) -> None:
        st.session_state.messages.append(
            {"role": "bot", "content": content, "citations": citations, "sources": sources, "time": time}
        )


    def add_user_message(self, content: str) -> None:
        st.session_state.messages.append({"role": "user", "content": content})

    def clear_chat_history(self) -> None:
        st.session_state.is_clear = True
        st.session_state.messages = []

    @property
    def is_clear(self) -> bool:
        if "clear" in st.session_state:
            return st.session_state.is_clear
        else:
            return False
        
class FileHelper:
    def __init__(self, cookie_manager: CookieManager) -> None:
        self.cookie_manager = cookie_manager
        st.session_state.file_states = self.file_states
        st.session_state.filenames = self.filenames

    @property
    def filenames(self) -> set[str]:
        if "filenames" in st.session_state:
            return st.session_state.filenames
        return set()
        
    @property
    def file_states(self) -> list[dict[str, bool | UploadedFile]]:
        if "file_states" in st.session_state:
            return st.session_state.file_states
        return []
    
    @staticmethod
    def has_file_been_uploaded(filename: str) -> bool:
        for file_state in st.session_state.file_states:
            if file_state["name"] == filename:
                return file_state["is_uploaded"]
        return False
    
    @staticmethod
    def update_file_is_uploaded(filename: str, is_uploaded: bool) -> None:
        for file_state in st.session_state.file_states:
            if file_state["name"] == filename:
                file_state["is_uploaded"] = is_uploaded
                return
    


    def save_files(self, files: list[UploadedFile]) -> None:
        unique_file_names = set()
        unique_files = []
        for file in files:
            if file.name in unique_file_names:
                continue
            unique_file_names.add(file.name)
            unique_files.append(file)
        st.session_state.file_states = [
            {"name": file.name, "file": file, "is_uploaded": self.has_file_been_uploaded(file.name)} for file in unique_files
        ]

    def upload_files(self) -> None:
        unuploaded_file_states =  [file_state for file_state in st.session_state.file_states if not file_state["is_uploaded"]]
        if len(unuploaded_file_states) == 0:
            return
        unuploaded_files = [file_state["file"] for file_state in unuploaded_file_states]
        result = Endpoints.upload_files(self.cookie_manager, unuploaded_files, st.session_state.sessionId)
        if result:
            for file_state in unuploaded_file_states:
                self.update_file_is_uploaded(file_state["name"], True)
    



class SessionStateHelper:
    def __init__(self) -> None:
        st.session_state.sessionId = self.sessionId
        st.session_state.authenticated = self.authenticated
        st.session_state.text_input_available = self.text_input_available
        self.cookie_manager = CookieManager()
        self.message_helper = MessageHelper(self.cookie_manager)
        self.file_helper = FileHelper(self.cookie_manager)
    
    @property
    def text_input_available(self) -> bool:
        if "text_input_available" in st.session_state:
            return st.session_state.text_input_available
        return False
    
    @text_input_available.setter
    def text_input_available(self, value: bool) -> None:
        st.session_state.text_input_available = value

    @property
    def sessionId(self) -> str:
        if "sessionId" in st.session_state:
            return st.session_state.sessionId
        return ""

    @sessionId.setter
    def sessionId(self, value: str) -> None:
        st.session_state.sessionId = value

    @property
    def authenticated(self) -> bool:
        if "authenticated" in st.session_state:
            return st.session_state.authenticated
        return False

    @authenticated.setter
    def authenticated(self, value: bool) -> None:
        st.session_state.authenticated = value
