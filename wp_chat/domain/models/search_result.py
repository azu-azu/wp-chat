"""
SearchResult Domain Model

Encapsulates the results of a search operation with metadata.
"""

from dataclasses import dataclass, field

from .document import Document


@dataclass
class SearchResult:
    """
    Search result domain model encapsulating search operation results.

    Contains:
    - Query information (query text, mode)
    - Search configuration (rerank status)
    - Retrieved documents
    - Metadata about the search operation
    """

    query: str
    mode: str
    documents: list[Document]
    rerank_enabled: bool = False
    total_candidates: int = 0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Set total_candidates if not explicitly provided."""
        if self.total_candidates == 0:
            self.total_candidates = len(self.documents)

    def get_top_k(self, k: int) -> list[Document]:
        """
        Get top-k most relevant documents.

        Args:
            k: Number of documents to return

        Returns:
            List of top-k documents
        """
        return self.documents[:k]

    def filter_by_relevance(self, threshold: float = 0.7) -> list[Document]:
        """
        Filter documents by relevance threshold.

        Args:
            threshold: Minimum relevance score (0.0-1.0)

        Returns:
            List of documents exceeding threshold
        """
        return [doc for doc in self.documents if doc.is_relevant(threshold)]

    def get_highly_relevant(self, threshold: float = 0.85) -> list[Document]:
        """
        Get highly relevant documents.

        Args:
            threshold: Minimum high relevance score (default: 0.85)

        Returns:
            List of highly relevant documents
        """
        return [doc for doc in self.documents if doc.is_highly_relevant(threshold)]

    def has_results(self) -> bool:
        """Check if search returned any results."""
        return len(self.documents) > 0

    def count(self) -> int:
        """Get number of documents in results."""
        return len(self.documents)

    def get_average_score(self) -> float:
        """
        Calculate average relevance score across all documents.

        Returns:
            Average score, or 0.0 if no documents
        """
        if not self.documents:
            return 0.0

        total = sum(doc.get_effective_score() for doc in self.documents)
        return total / len(self.documents)

    def get_unique_sources(self) -> set[str]:
        """
        Get unique source URLs from results.

        Returns:
            Set of unique URLs
        """
        return {doc.url for doc in self.documents}

    def to_dict(self) -> dict:
        """
        Convert search result to dictionary format for API responses.

        Returns:
            Dictionary with search result data
        """
        return {
            "query": self.query,
            "mode": self.mode,
            "rerank_enabled": self.rerank_enabled,
            "total_candidates": self.total_candidates,
            "result_count": self.count(),
            "documents": [doc.to_dict() for doc in self.documents],
            "metadata": self.metadata,
        }

    @classmethod
    def from_tuples(
        cls,
        query: str,
        mode: str,
        results: list[tuple[int, float, float | None]],
        meta: list[dict],
        rerank_enabled: bool = False,
    ) -> "SearchResult":
        """
        Create SearchResult from tuple format (backward compatibility).

        Args:
            query: Search query
            mode: Search mode (dense, bm25, hybrid)
            results: List of (idx, hybrid_score, ce_score) tuples
            meta: Metadata list for looking up document info
            rerank_enabled: Whether reranking was applied

        Returns:
            New SearchResult instance
        """
        documents = []
        for rank, (idx, hybrid_score, ce_score) in enumerate(results, 1):
            if 0 <= idx < len(meta):
                doc = Document.from_meta(
                    meta=meta[idx],
                    hybrid_score=hybrid_score,
                    ce_score=ce_score,
                    rank=rank,
                )
                documents.append(doc)

        return cls(
            query=query,
            mode=mode,
            documents=documents,
            rerank_enabled=rerank_enabled,
            total_candidates=len(results),
        )
