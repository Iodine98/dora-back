from dataclasses import dataclass, field
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
        return {"source": self.source, "page": self.page, "ranking": self.ranking, "score": self.score, "text": self.format_citation_text()}

    source: str
    page: int
    ranking: int
    score: float

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
    source_documents: list[Any]
    citations: set[Citation] = field(default_factory=set)
    with_proof: bool = True

    def __post_init__(self):
        """
        Initialize the citations.
        """
        self.get_unique_citations()
        
        

    def __dict__(self):
        """
        Return the citations as a dictionary.

        Returns:
            dict: The citations as a dictionary.
        """
        source_citations = [citation.__dict__() for citation in self.citations]
        source_citations.sort(key=lambda citation: citation["ranking"])
        return {"citations": source_citations, "with_proof": self.with_proof}

    
    def get_unique_citations(self):
        """
        Get the unique citations from the source documents.

        Iterate through the list of source documents and extract the source, page number, and proof for each document. Then, add the citation to the collection of unique citations.
        """

        for source_document in self.source_documents:
            raw_source = source_document.metadata["source"]
            source = Utils.remove_date_from_filename(Path(raw_source).name)
            page = source_document.metadata["page"] + 1
            proof = source_document.page_content
            ranking = source_document.metadata["ranking"]
            score = source_document.metadata["score"] if "score" in source_document.metadata else -1.0
            citation: Citation = ProofCitation(source, page, ranking, score, proof) if self.with_proof else BaseCitation(source, page, ranking, score)
            self.citations.add(citation)


    def print_citations(self):
        """
        Print the citations.

        This method iterates over the list of citations and prints the formatted citation text for each citation.
        """
        for citation in self.citations:
            print(citation.format_citation_text(), flush=True)
