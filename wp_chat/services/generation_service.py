"""
Generation Service - Encapsulates RAG generation business logic

This service handles:
- Search results to documents conversion
- Document preparation for generation pipeline
- Integration with generation pipeline and OpenAI client
"""

from typing import Any

from ..domain.models import Document


class GenerationService:
    """Service for handling RAG generation operations"""

    def __init__(self, meta: list[dict]):
        """
        Initialize generation service

        Args:
            meta: Document metadata
        """
        self.meta = meta

    def convert_hits_to_documents(
        self, hits: list[tuple], question: str
    ) -> tuple[list[dict[str, Any]], bool]:
        """
        Convert search hits to document format for generation

        Args:
            hits: Search results as list of tuples
                  Format: (idx, hybrid_score, ce_score) or (idx, score)
            question: User question (for context)

        Returns:
            Tuple of (documents, rerank_status)
            - documents: List of document dictionaries
            - rerank_status: Whether ce_score is present (indicates reranking was used)
        """
        docs = []
        rerank_status = False

        for rank, hit in enumerate(hits, 1):
            # Handle both formats: (idx, score, ce_score) and (idx, score)
            if len(hit) == 3:
                idx, hybrid_sc, ce_sc = hit
                if ce_sc is not None:
                    rerank_status = True
            else:
                idx, hybrid_sc = hit
                ce_sc = None

            # Validate index
            if idx < 0 or idx >= len(self.meta):
                continue

            # Get metadata
            m = self.meta[idx]

            # Build document dictionary
            doc = {
                "rank": rank,
                "hybrid_score": hybrid_sc,
                "post_id": m["post_id"],
                "chunk_id": m["chunk_id"],
                "title": m["title"],
                "url": m["url"],
                "snippet": self._create_snippet(m["chunk"]),
                "chunk": m["chunk"],
            }

            # Add ce_score if available (for A/B analysis)
            if ce_sc is not None:
                doc["ce_score"] = ce_sc

            docs.append(doc)

        return docs, rerank_status

    def _create_snippet(self, text: str, max_length: int = 400) -> str:
        """
        Create snippet from text

        Args:
            text: Full text
            max_length: Maximum snippet length

        Returns:
            Snippet with ellipsis if truncated
        """
        if len(text) <= max_length:
            return text
        return text[:max_length] + "…"

    def prepare_generation_context(
        self, search_results: list[tuple], question: str
    ) -> tuple[list[dict[str, Any]], bool]:
        """
        Prepare context for generation from search results

        This is a convenience method that wraps convert_hits_to_documents

        Args:
            search_results: Search results
            question: User question

        Returns:
            Tuple of (documents, rerank_status)
        """
        return self.convert_hits_to_documents(search_results, question)

    def prepare_from_domain_documents(self, documents: list[Document]) -> list[dict[str, Any]]:
        """
        Convert domain Document objects to generation-ready format.

        Args:
            documents: List of Document domain objects

        Returns:
            List of document dictionaries for generation pipeline
        """
        result = []
        for doc in documents:
            doc_dict = {
                "rank": doc.rank,
                "hybrid_score": doc.hybrid_score,
                "post_id": doc.post_id,
                "chunk_id": doc.chunk_id,
                "title": doc.title,
                "url": doc.url,
                "snippet": doc.create_snippet(),
                "chunk": doc.chunk,
            }

            # Add ce_score if available
            if doc.ce_score is not None:
                doc_dict["ce_score"] = doc.ce_score

            result.append(doc_dict)

        return result
