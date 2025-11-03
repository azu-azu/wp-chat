"""
GenerationResult Domain Model

Encapsulates the results of RAG generation with answer, references, and metrics.
"""

from dataclasses import dataclass, field


@dataclass
class GenerationResult:
    """
    Generation result domain model for RAG responses.

    Contains:
    - Generated answer text
    - Source references/citations
    - Generation metadata (latency, tokens, citations, etc.)
    """

    answer: str
    references: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def has_citations(self) -> bool:
        """Check if answer contains citations."""
        return self.metadata.get("has_citations", False)

    def citation_count(self) -> int:
        """Get number of citations in answer."""
        return self.metadata.get("citation_count", 0)

    def get_latency_ms(self) -> int:
        """Get generation latency in milliseconds."""
        return self.metadata.get("latency_ms", 0)

    def get_ttft_ms(self) -> int:
        """Get time to first token in milliseconds."""
        return self.metadata.get("ttft_ms", 0)

    def get_token_count(self) -> int:
        """Get total token count."""
        return self.metadata.get("token_count", 0)

    def get_model(self) -> str:
        """Get model used for generation."""
        return self.metadata.get("model", "unknown")

    def is_fallback(self) -> bool:
        """Check if result is from fallback mechanism."""
        return self.metadata.get("fallback", False)

    def has_error(self) -> bool:
        """Check if generation encountered errors."""
        return "error_message" in self.metadata

    def get_error_message(self) -> str | None:
        """Get error message if any."""
        return self.metadata.get("error_message")

    def reference_count(self) -> int:
        """Get number of references."""
        return len(self.references)

    def get_unique_sources(self) -> set[str]:
        """
        Get unique source URLs from references.

        Returns:
            Set of unique URLs
        """
        return {ref.get("url") for ref in self.references if "url" in ref}

    def calculate_answer_quality_score(self) -> float:
        """
        Calculate quality score based on citations and references.

        Returns:
            Score between 0.0 and 1.0
        """
        if self.is_fallback() or self.has_error():
            return 0.3

        # Base score
        score = 0.5

        # Bonus for citations
        if self.has_citations():
            citation_ratio = min(self.citation_count() / 5.0, 1.0)  # Max at 5 citations
            score += 0.3 * citation_ratio

        # Bonus for references
        if self.reference_count() > 0:
            ref_ratio = min(self.reference_count() / 3.0, 1.0)  # Max at 3 references
            score += 0.2 * ref_ratio

        return min(score, 1.0)

    def to_dict(self) -> dict:
        """
        Convert generation result to dictionary format for API responses.

        Returns:
            Dictionary with generation result data
        """
        return {
            "answer": self.answer,
            "references": self.references,
            "metadata": self.metadata,
        }

    @classmethod
    def create_success(
        cls,
        answer: str,
        references: list[dict],
        latency_ms: int,
        ttft_ms: int,
        token_count: int,
        model: str,
        citation_count: int,
        has_citations: bool,
        **extra_metadata,
    ) -> "GenerationResult":
        """
        Create successful generation result.

        Args:
            answer: Generated answer text
            references: List of reference dictionaries
            latency_ms: Total latency in milliseconds
            ttft_ms: Time to first token in milliseconds
            token_count: Total token count
            model: Model used for generation
            citation_count: Number of citations
            has_citations: Whether answer has citations
            **extra_metadata: Additional metadata fields

        Returns:
            New GenerationResult instance
        """
        metadata = {
            "latency_ms": latency_ms,
            "ttft_ms": ttft_ms,
            "token_count": token_count,
            "model": model,
            "citation_count": citation_count,
            "has_citations": has_citations,
            "fallback": False,
            **extra_metadata,
        }

        return cls(answer=answer, references=references, metadata=metadata)

    @classmethod
    def create_fallback(
        cls,
        answer: str,
        references: list[dict],
        error_message: str,
        latency_ms: int = 0,
        **extra_metadata,
    ) -> "GenerationResult":
        """
        Create fallback generation result (when generation fails).

        Args:
            answer: Fallback answer text
            references: List of reference dictionaries
            error_message: Error message explaining failure
            latency_ms: Total latency in milliseconds
            **extra_metadata: Additional metadata fields

        Returns:
            New GenerationResult instance with fallback flag
        """
        metadata = {
            "latency_ms": latency_ms,
            "ttft_ms": 0,
            "token_count": 0,
            "model": "fallback",
            "citation_count": 0,
            "has_citations": False,
            "fallback": True,
            "error_message": error_message,
            **extra_metadata,
        }

        return cls(answer=answer, references=references, metadata=metadata)
