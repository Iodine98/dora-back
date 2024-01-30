from streamlit_mods.helpers.session_state_helper import SessionStateHelper
from streamlit_mods.endpoints import Endpoints, Result
from typing import Any
import streamlit as st
from streamlit.delta_generator import DeltaGenerator
from timeit import default_timer
import time


class MainScreen:
    def __init__(self, session_state_helper: SessionStateHelper) -> None:
        self.session_state_helper = session_state_helper
        self.file_helper = session_state_helper.file_helper
        self.message_helper = session_state_helper.message_helper
        self.init_message_content = "Hallo, ik ben DoRA. Wat kan ik voor je doen?"
        self.init()

    def init(self):
        if not self.session_state_helper.authenticated:
            st.stop()
        self.add_initial_message()
        self.init_chat_input()
        self.display_messages()
        self.send_prompt_on_last_message()

    def display_messages(self):
        for message in self.message_helper.messages:
            if message["role"] == "human":
                with st.chat_message("human"):
                    st.markdown(message["content"])
            elif message["role"] == "ai":
                with st.chat_message("ai"):
                    st.markdown(message["content"])
                    if citations := message["citations"]:
                        for i, citation in enumerate(citations):
                            with st.expander(f"Bron {i+1}"):
                                st.markdown(f'Bestand: {citation["source"]}')
                                st.markdown(f'Pagina: {citation["page"]}')
                                st.markdown(f'Citaat: "{citation["proof"]}"')
                    time_elapsed = message["time"]
                    if time_elapsed == 0:
                        time_str = ""
                    elif time_elapsed > 100:
                        time_str = f"{round((time_elapsed)/60)} minuten"
                    else:
                        time_str = f"{round(time_elapsed)} seconden"
                    st.write(f":orange[Responstijd: {time_str}]" if time_str else "")

    def equals_init_message(self, message: dict[str, Any]) -> bool:
        return message["content"] == self.init_message_content

    def add_initial_message(self):
        if not self.session_state_helper.initialized:
            self.message_helper.add_bot_message(self.init_message_content, [], [], 0)
            self.session_state_helper.initialized = True

    def init_chat_input(self):
        if question := st.chat_input("Stel een vraag", key="chat_input"):
            self.message_helper.add_user_message(question)

    def send_prompt_on_last_message(self):
        last_message = self.message_helper.get_last_message()
        if last_message is None or not self.message_helper.is_message_prompt(last_message):
            return
        with st.chat_message("ai"):
            with st.spinner("Aan het denken..."):
                start = default_timer()
                result: Result | None = Endpoints.prompt(
                    self.session_state_helper.cookie_manager,
                    last_message["content"],
                    self.session_state_helper.sessionId,
                )
                if result is None:
                    st.error("Er ging iets mis bij het versturen van de vraag.")
                    return
            with st.spinner("Antwoord aan het formuleren..."):
                self.prepare_answer(*result, start)

    def prepare_answer(self, answer: str, citations: list[dict[str, str]], source_documents: Any, start_time: float):
        def build_placeholder() -> tuple[DeltaGenerator, str]:
            placeholder = st.empty()
            full_answer = ""
            for item in answer:
                full_answer += item
                placeholder.markdown(full_answer + "▌")
                time.sleep(0.1)
            return placeholder, full_answer

        def get_citations() -> None:
            for i, citation in enumerate(citations):
                with st.expander(f"Bron {i+1}"):
                    st.markdown(f'Bestand: {citation["source"]}')
                    st.markdown(f'Rangorde: {citation["ranking"]}')
                    st.markdown(f'Pagina: {citation["page"]}')
                    st.markdown(f'Citaat: "{citation["proof"]}"')

        def show_result() -> None:
            placeholder.markdown(full_answer)
            if citations:
                get_citations()
            time_str = f"{round((time_elapsed)/60)} minutes" if time_elapsed > 100 else f"{round(time_elapsed)} seconds"
            st.write(f":orange[Time to retrieve response: {time_str}]")

        placeholder, full_answer = build_placeholder()
        end = default_timer()
        time_elapsed = end - start_time
        self.message_helper.add_bot_message(answer, citations, source_documents, time_elapsed)
        show_result()
