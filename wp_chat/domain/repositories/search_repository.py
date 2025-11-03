"""
SearchRepository Interface

Abstract interface for search operations following the Repository Pattern.
Implementations can use FAISS, Elasticsearch, or any other search backend.
"""

from abc import ABC, abstractmethod

from ..models.search_result import SearchResult
from ..value_objects.query import Query


class SearchRepository(ABC):
    """
    Abstract repository interface for search operations.

    This interface defines the contract for search implementations,
    allowing the domain layer to remain independent of specific
    search technologies (FAISS, Elasticsearch, etc.).
    """

    @abstractmethod
    def search_dense(self, query: Query, topk: int) -> SearchResult:
        """
        Perform dense (semantic/vector) search.

        Args:
            query: Search query
            topk: Number of results to return

        Returns:
            SearchResult with retrieved documents

        Raises:
            SearchError: If search operation fails
        """
        pass

    @abstractmethod
    def search_sparse(self, query: Query, topk: int) -> SearchResult:
        """
        Perform sparse (keyword/BM25) search.

        Args:
            query: Search query
            topk: Number of results to return

        Returns:
            SearchResult with retrieved documents

        Raises:
            SearchError: If search operation fails
        """
        pass

    @abstractmethod
    def search_hybrid(
        self,
        query: Query,
        topk: int,
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4,
        rerank: bool = False,
        mmr_lambda: float = 0.7,
    ) -> SearchResult:
        """
        Perform hybrid search combining dense and sparse methods.

        Args:
            query: Search query
            topk: Number of results to return
            dense_weight: Weight for dense search scores (default: 0.6)
            sparse_weight: Weight for sparse search scores (default: 0.4)
            rerank: Whether to apply cross-encoder reranking
            mmr_lambda: Lambda parameter for MMR diversification (default: 0.7)

        Returns:
            SearchResult with retrieved and optionally reranked documents

        Raises:
            SearchError: If search operation fails
        """
        pass

    @abstractmethod
    def search(
        self,
        query: Query,
        topk: int,
        mode: str = "hybrid",
        rerank: bool = False,
    ) -> SearchResult:
        """
        Unified search interface supporting multiple modes.

        Args:
            query: Search query
            topk: Number of results to return
            mode: Search mode ("dense", "sparse", "hybrid")
            rerank: Whether to apply reranking (for hybrid mode)

        Returns:
            SearchResult with retrieved documents

        Raises:
            ValueError: If invalid mode is specified
            SearchError: If search operation fails
        """
        pass

    @abstractmethod
    def get_document_by_id(self, doc_id: str, chunk_id: int):
        """
        Retrieve specific document by ID.

        Args:
            doc_id: Document identifier
            chunk_id: Chunk identifier

        Returns:
            Document if found, None otherwise
        """
        pass

    @abstractmethod
    def count_documents(self) -> int:
        """
        Get total number of documents in index.

        Returns:
            Total document count
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if search backend is available.

        Returns:
            True if search backend is ready
        """
        pass


class SearchError(Exception):
    """Exception raised when search operations fail."""

    pass
