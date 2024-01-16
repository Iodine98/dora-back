from dataclasses import dataclass
from abc import abstractmethod
from typing import Any
from pathlib import Path
from chatdoc.utils import Utils


@dataclass(frozen=True)
class BaseCitation:
    """
    A citation for a source in a document.

    This class represents a citation for a source in a document. It contains information about the source and the page number where the citation is found.
    """

    def __dict__(self):
        """
        Return the citation as a dictionary.

        Returns:
            dict: The citation as a dictionary.
        """
        return {"source": self.source, "page": self.page, "text": self.format_citation_text()}

    source: str
    page: int

    @abstractmethod
    def format_citation_text(self):
        """
        Format the text from the citation.

        This method formats the text from the citation into a specific format. It returns a string that includes the source and the page number of the citation.
        """
        return f" - {self.source} on page {self.page}"


@dataclass(frozen=True)
class ProofCitation(BaseCitation):
    """
    A base citation with proof
    """

    def __dict__(self):
        """
        Return the citation as a dictionary.

        Returns:
            dict: The citation as a dictionary.
        """
        return {**super().__dict__(), "proof": self.proof,"text": self.format_citation_text()}

    proof: str

    def format_citation_text(self):
        """
        Format the text from the citation.

        Returns a formatted string containing the source, page number, and proof of the citation.
        """
        return f" - {self.source} on page {self.page}; PROOF: {self.proof}"


Citation = BaseCitation | ProofCitation


@dataclass
class Citations:
    """
    A set of citations.

    This class represents a collection of citations. It provides methods to add citations, get unique citations from source documents, and print the citations.
    """

    citations: set[Citation]
    with_proof: bool

    def __dict__(self):
        """
        Return the citations as a dictionary.

        Returns:
            dict: The citations as a dictionary.
        """
        return {"citations": [citation.__dict__() for citation in self.citations], "with_proof": self.with_proof}

    def add_citation(self, source: str, page: int, proof: str):
        """
        Add a citation to the set of citations.

        Args:
            source (str): The source of the citation.
            page (int): The page number of the citation.
            proof (str): The proof or evidence supporting the citation.

        """
        citation: Citation = ProofCitation(source, page, proof) if self.with_proof else BaseCitation(source, page)
        self.citations.add(citation)

    def get_unique_citations(self, source_documents: list[Any]):
        """
        Get the unique citations from the source documents.

        Iterate through the list of source documents and extract the source, page number, and proof for each document. Then, add the citation to the collection of unique citations.
        """
        for source_document in source_documents:
            raw_source = source_document.metadata["source"]
            source = Utils.remove_date_from_filename(Path(raw_source).name)
            page = source_document.metadata["page"] + 1
            proof = source_document.page_content
            self.add_citation(source, page, proof)

    def print_citations(self):
        """
        Print the citations.

        This method iterates over the list of citations and prints the formatted citation text for each citation.
        """
        for citation in self.citations:
            print(citation.format_citation_text(), flush=True)
