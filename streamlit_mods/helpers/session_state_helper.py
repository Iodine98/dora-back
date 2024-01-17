from typing import Any
import streamlit as st
from streamlit_cookies_manager import CookieManager
from streamlit_mods.helpers.file_helper import FileHelper
from streamlit_mods.helpers.message_helper import MessageHelper


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
