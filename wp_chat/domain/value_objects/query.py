"""
Query Value Object

Represents a search query with validation and normalization logic.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Query:
    """
    Query value object representing a validated search query.

    Immutable value object that ensures query validity and provides
    normalization utilities.
    """

    text: str

    def __post_init__(self):
        """Validate query on construction."""
        if not self.text or not self.text.strip():
            raise ValueError("Query text cannot be empty")

        if len(self.text) > 1000:
            raise ValueError("Query text exceeds maximum length of 1000 characters")

    def normalized(self) -> str:
        """
        Get normalized query text.

        Returns:
            Trimmed and normalized query string
        """
        return " ".join(self.text.strip().split())

    def length(self) -> int:
        """Get query length in characters."""
        return len(self.text)

    def word_count(self) -> int:
        """Get number of words in query."""
        return len(self.normalized().split())

    def is_short(self) -> bool:
        """Check if query is short (< 3 words)."""
        return self.word_count() < 3

    def is_long(self) -> bool:
        """Check if query is long (> 10 words)."""
        return self.word_count() > 10

    def contains(self, substring: str) -> bool:
        """
        Check if query contains substring (case-insensitive).

        Args:
            substring: Substring to search for

        Returns:
            True if substring found
        """
        return substring.lower() in self.text.lower()

    def starts_with(self, prefix: str) -> bool:
        """
        Check if query starts with prefix (case-insensitive).

        Args:
            prefix: Prefix to check

        Returns:
            True if query starts with prefix
        """
        return self.normalized().lower().startswith(prefix.lower())

    def to_lowercase(self) -> str:
        """Get lowercase version of normalized query."""
        return self.normalized().lower()

    def __str__(self) -> str:
        """String representation returns normalized text."""
        return self.normalized()

    def __len__(self) -> int:
        """Support len() function."""
        return self.length()

    @classmethod
    def from_string(cls, text: str) -> "Query":
        """
        Create Query from string with automatic normalization.

        Args:
            text: Query text

        Returns:
            New Query instance

        Raises:
            ValueError: If query is invalid
        """
        return cls(text=text.strip())
