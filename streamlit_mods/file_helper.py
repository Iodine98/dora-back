from streamlit_cookies_manager import CookieManager
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from streamlit_mods.endpoints import Endpoints

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
        st.session_state.filenames = unique_file_names
        st.session_state.file_states = [
            {"name": file.name, "file": file, "is_uploaded": self.has_file_been_uploaded(file.name)} for file in unique_files
        ]

    def upload_files(self) -> None:
        unuploaded_file_states =  [file_state for file_state in st.session_state.file_states if not file_state["is_uploaded"]]
        if len(unuploaded_file_states) == 0:
            return
        with st.spinner("Bestanden uploaden..."):
            unuploaded_files = [file_state["file"] for file_state in unuploaded_file_states]
            result = Endpoints.upload_files(self.cookie_manager, unuploaded_files, st.session_state.sessionId)
            if result:
                for file_state in unuploaded_file_states:
                    self.update_file_is_uploaded(file_state["name"], True)