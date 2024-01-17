import random
import random
from typing import Any
import streamlit as st
from streamlit_cookies_manager import CookieManager
from streamlit_mods.endpoints import Endpoints
from streamlit_mods.helpers.file_helper import FileHelper
from streamlit_mods.helpers.message_helper import MessageHelper
from streamlit.runtime.uploaded_file_manager import UploadedFile


class SessionStateHelper:
    def __init__(self) -> None:
        st.session_state.sessionId = self.sessionId
        st.session_state.authenticated = self.authenticated
        st.session_state.initialized = self.initialized
        st.session_state.text_input_available = self.text_input_available
        st.session_state.file_uploader_key = self.file_uploader_key
        st.session_state.file_uploader_key = self.file_uploader_key
        self.cookie_manager = CookieManager()
        self.message_helper = MessageHelper(self.cookie_manager)
        self.file_helper = FileHelper(self.cookie_manager)

    @property
    def initialized(self) -> bool:
        if "initialized" in st.session_state:
            return st.session_state.initialized
        return False

    @initialized.setter
    def initialized(self, value: bool) -> None:
        st.session_state.initialized = value

    @property
    def file_uploader_key(self) -> int:
        if "file_uploader_key" in st.session_state:
            return st.session_state.file_uploader_key
        return random.randint(0, 100000)

    @file_uploader_key.setter
    def file_uploader_key(self, value: int) -> None:
        st.session_state.file_uploader_key = value

    @property
    def text_input_available(self) -> bool:
        if "text_input_available" in st.session_state:
            return st.session_state.text_input_available
        return True

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

    def clear_chat_history(self) -> None:
        result = Endpoints.clear_chat_history(self.cookie_manager, self.sessionId)
        if result:
            self.messages = []
            for filename in self.file_helper.filenames:
                self.file_helper.delete_file(filename)
            self.file_helper.filenames = set()
            self.file_uploader_key = random.randint(0, 100000)

    def on_file_remove(self) -> None:
        new_files: list[UploadedFile] = st.session_state[self.file_uploader_key]
        new_file_names = set(file.name for file in new_files)
        old_file_names = self.file_helper.filenames
        removed_file_names = old_file_names - new_file_names
        if removed_file_names:
            for removed_file_name in removed_file_names:
                self.file_helper.delete_file(removed_file_name)
            self.file_helper.filenames = new_file_names
