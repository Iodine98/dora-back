from .session_state_helper import SessionStateHelper
from .endpoints import Endpoints, Result
from typing import Any
import streamlit as st
from streamlit.delta_generator import DeltaGenerator
from streamlit.runtime.uploaded_file_manager import UploadedFile
from timeit import default_timer
from pathlib import Path
import time

class AppLayout:
    def __init__(self, session_state_helper: SessionStateHelper) -> None:
        st.title("DoRA (Documenten Raadplegen Assistent)")
        self.session_state_helper = session_state_helper
        self.message_helper = session_state_helper.message_helper
        self.file_helper = session_state_helper.file_helper
        self.init_message_content = "Hallo, ik ben DoRA. Wat kan ik voor je doen?"

    def equals_init_message(self, message: dict[str, Any]) -> bool:
        return message["content"] == self.init_message_content
    
    def is_message_prompt(self, message: dict[str, Any]) -> bool:
        """
        Validating if a message counts as a user prompt.
        Only if:
        1) The role of the message (i.e. the sender) is 'user'
        2) 'content' exists as an attribute of message
        3) The message content is a string
        4) The message content is not empty
        """
        return message is not None \
            and message["role"] == "user" \
            and "content" in message \
            and isinstance(message["content"], str) \
            and message["content"] != ""

    def identify(self):
        json_response: dict[str, Any] | None = Endpoints.identify(self.session_state_helper.cookie_manager, session_id=self.session_state_helper.sessionId)
        if json_response is None:
            return
        self.session_state_helper.authenticated = json_response["authenticated"]
        self.session_state_helper.sessionId = json_response["sessionId"]

    def show_initial_message(self):
        last_message = self.message_helper.get_last_message() 
        if last_message is None or not self.equals_init_message(last_message):
            with st.chat_message("bot"):
                st.write(self.init_message_content)
            self.message_helper.add_bot_message(self.init_message_content, [], [], 0)

    def initialize_file_uploader(self) -> list[UploadedFile] | None:
        if uploaded_files := st.file_uploader(
            "Upload een of meerdere documenten",
            type=["pdf", "docx", "doc", "txt"],
            accept_multiple_files=True,
        ):
            self.file_helper.save_files(uploaded_files)
            return uploaded_files
        return None
    
    def initialize_file_downloader(self, files: list[UploadedFile] | None):
        if files is None:
            return
        for file in files:
            file_path = Path(file.name)
            file_name = file_path.name
            file_bytes = file.getvalue()
            st.download_button(
                label=f"Download {file_name}",
                data=file_bytes,
                file_name=file_name,
                mime="application/octet-stream",
            )
        

    def initialize_sidebar(self):
        if not self.session_state_helper.authenticated:
            st.stop()
        self.file_helper.upload_files()
        with st.sidebar:
            files = self.initialize_file_uploader()
            self.initialize_file_downloader(files)
            st.sidebar.button("Verwijder chatgeschiedenis", 
                              on_click=self.message_helper.clear_chat_history,
                              disabled=self.message_helper.is_clear)
        
        


    def init_chat_input(self):
        if question := st.text_input("Stel een vraag",
                                     key="chat_input"):
            
            self.message_helper.add_user_message(question)
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
        self.message_helper.add_bot_message(answer, citations, source_documents, time_elapsed)
        self.show_result(placeholder, full_answer, citations, source_documents, time_elapsed)

    def send_prompt_on_last_message(self):
        last_message = self.message_helper.get_last_message()
        if last_message is None or not self.is_message_prompt(last_message):
                return
        with st.chat_message("bot"):
            with st.spinner("Thinking..."):
                start = default_timer()
                result: Result | None = Endpoints.prompt(self.session_state_helper.cookie_manager, last_message["content"], self.session_state_helper.sessionId)
                if result is None:
                    st.error("Er ging iets mis bij het versturen van de vraag.")
                    return
                self.prepare_answer(*result, start)
        
        
    def get_citations(self, citations: list[dict[str, str]]) -> None:
        for i, citation in enumerate(citations):
            with st.expander(f"Bron {i+1}"):
                st.markdown(f'Bestand: {citation["source"]}')
                st.markdown(f'Pagina: {citation["page"]}')
                st.markdown(f'Citaat: \"{citation["proof"]}\"')

    def show_result(
        self, container: DeltaGenerator, answer: str, citations: list[dict[str, str]], sources: Any, time: float
    ) -> None:
        container.markdown(answer)
        if citations:
            self.get_citations(citations)
        time_str = f"{round((time)/60)} minutes" if time > 100 else f"{round(time)} seconds"
        st.write(f":orange[Time to retrieve response: {time_str}]")

    def initialize_main(self):
        if not self.session_state_helper.authenticated:
            st.stop()
        self.show_initial_message()
        self.init_chat_input()
        self.send_prompt_on_last_message()
        
        
