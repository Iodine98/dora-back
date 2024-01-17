from streamlit_mods.components.sidebar import Sidebar
from streamlit_mods.components.main_screen import MainScreen
from .helpers.session_state_helper import SessionStateHelper
from .endpoints import Endpoints, Result
from typing import Any
import streamlit as st


class AppLayout:
    def __init__(self, session_state_helper: SessionStateHelper) -> None:
        st.title("DoRA (Documenten Raadplegen Assistent)")
        self.session_state_helper = session_state_helper
        self.message_helper = session_state_helper.message_helper
        self.file_helper = session_state_helper.file_helper

    def identify(self):
        json_response: dict[str, Any] | None = Endpoints.identify(
            self.session_state_helper.cookie_manager, session_id=self.session_state_helper.sessionId
        )
        if json_response is None:
            return
        self.session_state_helper.authenticated = json_response["authenticated"]
        self.session_state_helper.sessionId = json_response["sessionId"]

    def initialize_sidebar(self):
        Sidebar(self.session_state_helper)

    def initialize_main(self):
        MainScreen(self.session_state_helper)
