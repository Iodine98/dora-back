from typing import Any
import streamlit as st

class SessionStateHelper:
    def __init__(self) -> None:
        st.session_state.sessionId = self.sessionId
        st.session_state.authenticated = self.authenticated
        st.session_state.messages = self.messages
        st.session_state.is_clear = self.is_clear
        

    @property
    def is_clear(self) -> bool:
        if "clear" in st.session_state:
            return st.session_state.is_clear
        else:
            return False

    
    @property
    def messages(self) -> list:
        if "messages" in st.session_state:
            return st.session_state.messages
        return []
    

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
        st.session_state.is_clear = True
        st.session_state.messages = []

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