from ..helpers.session_state_helper import SessionStateHelper
from streamlit.runtime.uploaded_file_manager import UploadedFile
import streamlit as st
from pathlib import Path


class Sidebar:
    def __init__(self, session_state_helper: SessionStateHelper) -> None:
        self.session_state_helper = session_state_helper
        self.file_helper = session_state_helper.file_helper
        self.message_helper = session_state_helper.message_helper
        self.init()

    def init(self):
        if not self.session_state_helper.authenticated:
            st.stop()
        with st.sidebar:
            files = self.initialize_file_uploader()
            self.initialize_file_downloader(files)
            st.sidebar.button(
                "Verwijder chatgeschiedenis",
                on_click=self.message_helper.clear_chat_history,
                args=(self.session_state_helper.sessionId,),
            )

    def initialize_file_uploader(self) -> list[UploadedFile] | None:
        css = """
            <style>
            [data-testid="stFileUploadDropzone"] div div::before {content:"Sleep uw bestanden hierheen"}
            [data-testid="stFileUploadDropzone"] div div span{display:none;}
            [data-testid="stFileUploadDropzone"] div div::after {content:"Maximaal 200 MB per bestand"}
            [data-testid="stFileUploadDropzone"] div div small{display:none;}
            [data-testid="stFileUploadDropzone"] button{display:none;}
            </style>
            """
        st.markdown(css, unsafe_allow_html=True)
        if uploaded_files := st.file_uploader(
            "Upload uw bestanden hier",
            type=["pdf", "docx", "doc", "txt"],
            accept_multiple_files=True,
        ):
            self.file_helper.save_files(uploaded_files)
            self.file_helper.upload_files()
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
