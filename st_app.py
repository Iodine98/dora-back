import time
import streamlit as st
from typing import Any
import requests
from streamlit.runtime.uploaded_file_manager import UploadedFile
from streamlit.delta_generator import DeltaGenerator
import extra_streamlit_components as stx
from timeit import default_timer

Result = tuple[str, list[dict[str, str]], Any]


@st.cache_resource
def get_manager():
    return stx.CookieManager()


class SessionStateHelper:
    def __init__(self) -> None:
        st.session_state.sessionId = ""
        st.session_state.authenticated = False
        st.session_state.messages = []
        st.session_state["clear"] = False

    @property
    def sessionId(self) -> str:
        return st.session_state.sessionId

    @sessionId.setter
    def sessionId(self, value: str) -> None:
        st.session_state.sessionId = value

    @property
    def authenticated(self) -> bool:
        return st.session_state.authenticated

    @authenticated.setter
    def authenticated(self, value: bool) -> None:
        st.session_state.authenticated = value

    def clear_chat_history(self) -> None:
        st.session_state["clear"] = True
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


class Endpoints:
    @staticmethod
    def identify() -> dict[str, Any] | None:
        try:
            response = requests.get("http://127.0.0.1:5000/identify")
            json_response = response.json()
            if json_response["error"] != "":
                st.error(json_response["error"])
                return
            response_message = json_response["message"]
            st.toast(response_message, icon="🤗")
            return json_response
        except Exception as err:
            st.error(err, icon="❌")

    @staticmethod
    def upload_files(uploaded_files: list[UploadedFile], session_id: str | None = None) -> None:
        prefix = "file_"
        files_with_prefix = {prefix + file.name: file.getvalue() for file in uploaded_files}
        session_id_dict = {"sessionId": session_id} if session_id else {}
        form_data = {
            "prefix": prefix,
              **session_id_dict,
                **files_with_prefix
                }
        try:
            response = requests.post("http://127.0.0.1:5000/upload_files", data=form_data)
            json_response = response.json()
            if json_response["error"] != "":
                st.error(json_response["error"], icon="❌")
                return
            response_message = json_response["message"]
            st.toast(response_message, icon="✅")
        except Exception as err:
            st.error(err, icon="❌")

    @staticmethod
    def prompt(text_prompt: str) -> Result | None:
        try:
            response = requests.post("http://127.0.0.1:5000/prompt", files={"prompt": text_prompt})
            json_response = response.json()
            if json_response["error"] != "":
                st.error(json_response["error"], icon="❌")
                return None
            result = json_response["result"]
            citations = result["citations"]
            source_docs = result["source_documents"]
            answer = result["answer"]
            return answer, citations, source_docs
        except Exception as err:
            st.error(err)


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
            st.sidebar.button("Verwijder chatgeschiedenis", on_click=self.session_state_helper.clear_chat_history)

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

    def send_prompt_on_last_message(self):
        last_message = self.session_state_helper.get_last_message()
        if last_message is None or self.equals_init_message(last_message):
            return
        match last_message["role"]:
            case "user":
                pass
            case "bot":
                with st.chat_message("bot"):
                    with st.spinner("Thinking...:thinking:"):
                        if "content" in last_message and last_message["content"] is not None:
                            start = default_timer()
                            result = Endpoints.prompt(last_message["content"])
                            if result is None:
                                st.error("Er ging iets mis bij het versturen van de vraag.")
                                return
                            answer, citations, source_documents = result
                            placeholder, full_answer = self.build_placeholder(answer)
                            end = default_timer()
                            time_elapsed = end - start
                            self.session_state_helper.add_bot_message(answer, citations, source_documents, time_elapsed)
                            self.show_result(placeholder, full_answer, citations, source_documents, time_elapsed)

            case x:
                raise NotImplementedError(f"Message role {str(x)} has not been implemented.")

    def get_sources(self, sources: Any) -> None:
        for i, source in enumerate(sources):
            with st.expander(f"Bron {i+1}"):
                st.markdown(f'Document naam: {source["document_name"]}')
                st.markdown(f'Brontekst: {source["source_text"]}')
                if "page" in source.metadata:
                    st.markdown(f'Pagina: {source.metadata["page"] + 1}\n')
                if st.button("Bekijk document"):
                    try:
                        st.markdown(
                            """
                            <script>
                                    window.open(arguments[0], "_blank");
                            </script>
                            """,
                            unsafe_allow_html=True,
                        )
                    except Exception as e:
                        st.error(e)

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


def main():
    session_state_helper = SessionStateHelper()
    app_layout = AppLayout(session_state_helper)
    if not session_state_helper.authenticated:
        app_layout.identify()
    app_layout.initialize_sidebar()
    app_layout.initialize_main()


if __name__ == "__main__":
    main()
