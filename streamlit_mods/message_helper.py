import streamlit as st
from typing import Any
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
 