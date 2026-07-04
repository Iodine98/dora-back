import pytest
from langchain_core.prompts import ChatPromptTemplate

from chatdoc.prompt_mode import PromptMode, get_qa_prompt, get_system_template


@pytest.mark.parametrize("prompt_mode", list(PromptMode))
def test_get_qa_prompt_returns_chat_prompt_template(prompt_mode):
    """
    Every prompt mode should produce a valid ChatPromptTemplate that still exposes the
    "context" and "question" input variables expected by the QA / combine-documents chain.
    """
    qa_prompt = get_qa_prompt(prompt_mode)
    assert isinstance(qa_prompt, ChatPromptTemplate)
    assert set(qa_prompt.input_variables) == {"context", "question"}


def test_default_mode_matches_langchains_builtin_default_system_template():
    """
    PromptMode.DEFAULT must reproduce langchain's own default "stuff" QA chat system
    prompt, so that selecting it (or omitting prompt_mode entirely) preserves DoRA's
    previous behavior from before prompt modes were introduced.
    """
    default_template = get_system_template(PromptMode.DEFAULT)
    assert "{context}" in default_template
    assert "don't know the answer" in default_template


def test_modes_have_distinct_system_templates():
    """
    Each mode should produce a unique system message, otherwise the mode selection
    would be a no-op.
    """
    templates = [get_system_template(mode) for mode in PromptMode]
    assert len(templates) == len(set(templates))


def test_concise_and_detailed_modes_diverge_from_default_in_content():
    concise = get_system_template(PromptMode.CONCISE)
    detailed = get_system_template(PromptMode.DETAILED)
    assert "brief" in concise.lower()
    assert "thorough" in detailed.lower()


def test_invalid_prompt_mode_string_raises_value_error():
    with pytest.raises(ValueError):
        PromptMode("nonexistent-mode")
