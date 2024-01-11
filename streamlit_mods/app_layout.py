from .session_state_helper import SessionStateHelper
from .endpoints import Endpoints, Result
from typing import Any
import streamlit as st
from streamlit.delta_generator import DeltaGenerator
from timeit import default_timer
import time

class AppLayout:
    def __init__(self, session_state_helper: SessionStateHelper) -> None:
        st.title("DoRA (Documenten Raadplegen Assistent)")
        self.session_state_helper = session_state_helper
        self.init_message_content = "Hallo, ik ben DoRA. Wat kan ik voor je doen?"

    def equals_init_message(self, message: dict[str, Any]) -> bool:
        return message["content"] == self.init_message_content

    def identify(self):
        json_response: dict[str, Any] | None = Endpoints.identify()
        if json_response is None:
            return
        self.session_state_helper.authenticated = json_response["authenticated"]
        self.session_state_helper.sessionId = json_response["sessionId"]

    def show_initial_message(self):
        if self.session_state_helper.authenticated:
            return
        with st.chat_message("bot"):
            st.write(self.init_message_content)
        self.session_state_helper.add_bot_message(self.init_message_content, [], [], 0)

    def initialize_sidebar(self):
        with st.sidebar:
            uploaded_files = st.sidebar.file_uploader(
                "Upload een of meerdere documenten",
                type=["pdf", "docx", "doc", "txt"],
                accept_multiple_files=True,
            )
            if uploaded_files and isinstance(uploaded_files, list):
                Endpoints.upload_files(uploaded_files, session_id=self.session_state_helper.sessionId)
            st.sidebar.button("Verwijder chatgeschiedenis", 
                              on_click=self.session_state_helper.clear_chat_history,
                              disabled=self.session_state_helper.is_clear)

    def init_chat_input(self):
        if question := st.text_input("Stel een vraag"):
            self.session_state_helper.add_user_message(question)
            with st.chat_message("user"):
                st.write(question)

    @staticmethod
    def build_placeholder(answer: str) -> tuple[DeltaGenerator, str]:
        placeholder = st.empty()
        full_answer = ""
        for item in answer:
            full_answer += item
            placeholder.markdown(full_answer + "▌")
            time.sleep(0.1)
        return placeholder, full_answer
    

    def prepare_answer(self, answer: str, citations: list[dict[str, str]], source_documents: Any, start_time: float):
        placeholder, full_answer = self.build_placeholder(answer)
        end = default_timer()
        time_elapsed = end - start_time
        self.session_state_helper.add_bot_message(answer, citations, source_documents, time_elapsed)
        self.show_result(placeholder, full_answer, citations, source_documents, time_elapsed)

    def send_prompt_on_last_message(self):
        last_message = self.session_state_helper.get_last_message()
        if last_message is None or \
            self.equals_init_message(last_message) or \
            last_message["role"] != "bot" or \
            "content" not in last_message or \
            last_message["content"] is None:
                return
        with st.chat_message("bot"):
            with st.spinner("Thinking...:thinking:"):
                start = default_timer()
                result: Result | None = Endpoints.prompt(last_message["content"])
                if result is None:
                    st.error("Er ging iets mis bij het versturen van de vraag.")
                    return
                self.prepare_answer(*result, start)
        
    def get_sources(self, sources: Any) -> None:
        for i, source in enumerate(sources):
            with st.expander(f"Bron {i+1}"):
                st.markdown(f'Document naam: {source["document_name"]}')
                st.markdown(f'Brontekst: {source["source_text"]}')
                if "page" in source.metadata:
                    st.markdown(f'Pagina: {source.metadata["page"] + 1}\n')
                st.download_button("Bekijk document", source)

    def show_result(
        self, container: DeltaGenerator, answer: str, citations: list[dict[str, str]], sources: Any, time: float
    ) -> None:
        container.markdown(answer)
        if sources:
            self.get_sources(sources)
        time_str = f"{round((time)/60)} minutes" if time > 100 else f"{round(time)} seconds"
        st.write(f":orange[Time to retrieve response: {time_str}]")

    def initialize_main(self):
        self.show_initial_message()
        self.init_chat_input()
        self.send_prompt_on_last_message()
