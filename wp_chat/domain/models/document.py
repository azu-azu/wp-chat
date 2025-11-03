"""
Document Domain Model

Represents a searchable document chunk with its metadata and relevance scores.
"""

from dataclasses import dataclass


@dataclass
class Document:
    """
    Document domain model representing a searchable content chunk.

    This is the core entity in the search domain, containing:
    - Document identification (post_id, chunk_id)
    - Content and metadata (title, url, chunk)
    - Relevance scores (hybrid_score, ce_score)
    """

    post_id: str
    chunk_id: int
    title: str
    url: str
    chunk: str
    hybrid_score: float
    ce_score: float | None = None
    rank: int | None = None

    def is_relevant(self, threshold: float = 0.7) -> bool:
        """
        Determine if document is relevant based on hybrid score.

        Args:
            threshold: Minimum score to be considered relevant (0.0-1.0)

        Returns:
            True if document exceeds relevance threshold
        """
        return self.hybrid_score >= threshold

    def is_highly_relevant(self, threshold: float = 0.85) -> bool:
        """
        Determine if document is highly relevant.

        Args:
            threshold: Minimum score for high relevance (default: 0.85)

        Returns:
            True if document exceeds high relevance threshold
        """
        return self.hybrid_score >= threshold

    def has_rerank_score(self) -> bool:
        """Check if document has been reranked with cross-encoder."""
        return self.ce_score is not None

    def get_effective_score(self) -> float:
        """
        Get the most appropriate score for ranking.

        Returns ce_score if available (more accurate),
        otherwise returns hybrid_score.
        """
        return self.ce_score if self.ce_score is not None else self.hybrid_score

    def create_snippet(self, max_length: int = 400) -> str:
        """
        Create a text snippet from the document chunk.

        Args:
            max_length: Maximum length of snippet

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(self.chunk) <= max_length:
            return self.chunk
        return self.chunk[:max_length] + "…"

    def to_dict(self) -> dict:
        """
        Convert document to dictionary format for API responses.

        Returns:
            Dictionary with document data
        """
        result = {
            "post_id": self.post_id,
            "chunk_id": self.chunk_id,
            "title": self.title,
            "url": self.url,
            "chunk": self.chunk,
            "hybrid_score": self.hybrid_score,
        }

        if self.rank is not None:
            result["rank"] = self.rank

        if self.ce_score is not None:
            result["ce_score"] = self.ce_score

        return result

    @classmethod
    def from_meta(
        cls,
        meta: dict,
        hybrid_score: float,
        ce_score: float | None = None,
        rank: int | None = None,
    ) -> "Document":
        """
        Create Document from metadata dictionary.

        Args:
            meta: Metadata dictionary with post_id, chunk_id, title, url, chunk
            hybrid_score: Hybrid search score
            ce_score: Optional cross-encoder rerank score
            rank: Optional ranking position

        Returns:
            New Document instance
        """
        return cls(
            post_id=meta["post_id"],
            chunk_id=meta["chunk_id"],
            title=meta["title"],
            url=meta["url"],
            chunk=meta["chunk"],
            hybrid_score=hybrid_score,
            ce_score=ce_score,
            rank=rank,
        )
