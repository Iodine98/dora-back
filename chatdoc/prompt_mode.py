"""
Module defining a small, curated set of selectable "prompt modes" for the Chatbot.

See GitHub issue #48: rather than letting users supply an arbitrary, free-form prompt
template string (which would let user input leak directly into the instructions sent to
the underlying LLM), DoRA exposes a fixed enum of vetted system messages. Users/callers
pick a mode by name, and the corresponding curated system prompt is used.
"""
from enum import Enum

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.chat import HumanMessagePromptTemplate, SystemMessagePromptTemplate

# This matches langchain's own default "stuff" QA chat prompt, so PromptMode.DEFAULT
# preserves the exact behavior DoRA had before prompt modes were introduced.
_DEFAULT_SYSTEM_TEMPLATE = """Use the following pieces of context to answer the user's question. \
If you don't know the answer, just say that you don't know, don't try to make up an answer.
----------------
{context}"""

_CONCISE_SYSTEM_TEMPLATE = """Use the following pieces of context to answer the user's question as briefly \
as possible. Answer in as few sentences as you can, do not repeat the question, and do not add \
information that was not asked for. If you don't know the answer, just say that you don't know, \
don't try to make up an answer.
----------------
{context}"""

_DETAILED_SYSTEM_TEMPLATE = """Use the following pieces of context to answer the user's question as \
thoroughly as possible. Explain your reasoning, mention relevant caveats or nuances found in the \
context, and structure longer answers using short paragraphs or bullet points where it helps \
readability. If you don't know the answer, just say that you don't know, don't try to make up an \
answer.
----------------
{context}"""


class PromptMode(str, Enum):
    """
    A curated set of system messages that steer the tone and depth of the chatbot's answers.
    """

    DEFAULT = "default"
    CONCISE = "concise"
    DETAILED = "detailed"


_SYSTEM_TEMPLATES: dict["PromptMode", str] = {
    PromptMode.DEFAULT: _DEFAULT_SYSTEM_TEMPLATE,
    PromptMode.CONCISE: _CONCISE_SYSTEM_TEMPLATE,
    PromptMode.DETAILED: _DETAILED_SYSTEM_TEMPLATE,
}


def get_system_template(prompt_mode: PromptMode) -> str:
    """
    Return the raw system-message template string associated with the given PromptMode.
    """
    return _SYSTEM_TEMPLATES[prompt_mode]


def get_qa_prompt(prompt_mode: PromptMode) -> ChatPromptTemplate:
    """
    Build the chat prompt template used by the "combine documents" (QA) step of the
    ConversationalRetrievalChain for the given PromptMode.
    """
    system_template = get_system_template(prompt_mode)
    messages = [
        SystemMessagePromptTemplate.from_template(system_template),
        HumanMessagePromptTemplate.from_template("{question}"),
    ]
    return ChatPromptTemplate.from_messages(messages)
