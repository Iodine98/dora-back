import pytest  # pylint: disable=unused-import
from chatdoc.citation import BaseCitation, ProofCitation


def test_base_citation():
    """
    Test case for the BaseCitation class.

    This test verifies that the BaseCitation object is created correctly and that the
    `source`, `page`, and `format_citation_text` attributes behave as expected.
    """
    base_citation = BaseCitation("Source", 1, 1, -1)
    assert base_citation.source == "Source"
    assert base_citation.page == 1
    assert base_citation.format_citation_text() == " - Source on page 1"


def test_proof_citation():
    """
    Test case for the ProofCitation class.

    This test verifies that the ProofCitation object is created correctly and that the format_citation_text method returns the expected result.
    """
    proof_citation = ProofCitation("Source", 1, 1, -1, "Just because")
    assert proof_citation.source == "Source"
    assert proof_citation.page == 1
    # Assuming ProofCitation implements format_citation_text method
    assert proof_citation.format_citation_text() == " - Source on page 1; PROOF: Just because"
