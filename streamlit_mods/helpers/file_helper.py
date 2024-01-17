from typing import cast
from streamlit_cookies_manager import CookieManager
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from streamlit_mods.endpoints import Endpoints


class FileHelper:
    def __init__(self, cookie_manager: CookieManager) -> None:
        self.cookie_manager = cookie_manager
        st.session_state.file_states = self.file_states
        st.session_state.filenames = self.filenames
        st.session_state.file_id_mapping = self.file_id_mapping

    @property
    def file_id_mapping(self) -> dict[str, list[str]]:
        if "file_id_mapping" in st.session_state:
            return st.session_state.file_id_mapping
        return {}

    @file_id_mapping.setter
    def file_id_mapping(self, value: dict[str, list[str]]) -> None:
        st.session_state.file_id_mapping = value

    @property
    def filenames(self) -> set[str]:
        if "filenames" in st.session_state:
            return st.session_state.filenames
        return set()

    @filenames.setter
    def filenames(self, value: set[str]) -> None:
        st.session_state.filenames = value

    @property
    def file_states(self) -> list[dict[str, bool | UploadedFile | str]]:
        if "file_states" in st.session_state:
            return st.session_state.file_states
        return []

    @file_states.setter
    def file_states(self, value: list[dict[str, bool | UploadedFile | str]]) -> None:
        st.session_state.file_states = value

    def has_file_been_uploaded(self, filename: str) -> bool:
        for file_state in self.file_states:
            if file_state["name"] == filename:
                return bool(file_state["is_uploaded"])
        return False

    def update_file_is_uploaded(self, filename: str, is_uploaded: bool) -> None:
        for file_state in self.file_states:
            if file_state["name"] == filename:
                file_state["is_uploaded"] = is_uploaded
                return

    def save_files(self, files: list[UploadedFile]) -> list[UploadedFile]:
        unique_file_names = set()
        unique_files = []
        for file in files:
            if file.name in unique_file_names:
                continue
            unique_file_names.add(file.name)
            unique_files.append(file)
        self.filenames = unique_file_names
        self.file_states = [
            {"name": file.name, "file": file, "is_uploaded": self.has_file_been_uploaded(file.name)}
            for file in unique_files
        ]
        return unique_files

    def upload_files(self) -> None:
        unuploaded_file_states = [file_state for file_state in self.file_states if not file_state["is_uploaded"]]
        if len(unuploaded_file_states) == 0:
            return
        with st.spinner("Bestanden uploaden..."):
            unuploaded_files = [cast(UploadedFile, file_state["file"]) for file_state in unuploaded_file_states]
            result = Endpoints.upload_files(self.cookie_manager, unuploaded_files, st.session_state.sessionId)
            if result:
                for file_state in unuploaded_file_states:
                    self.update_file_is_uploaded(cast(str, file_state["name"]), True)
                self.file_id_mapping = result

    def delete_file(self, filename: str) -> None:
        result = Endpoints.delete_file(
            self.cookie_manager, filename, self.file_id_mapping[filename], st.session_state.sessionId
        )
        if result:
            self.file_states = [file_state for file_state in self.file_states if file_state["name"] != filename]
            self.file_id_mapping = {
                filename: document_ids
                for filename, document_ids in self.file_id_mapping.items()
                if filename != filename
            }
