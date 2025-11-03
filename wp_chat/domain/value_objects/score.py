"""
Score Value Object

Represents a relevance score with validation and comparison logic.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, order=True)
class Score:
    """
    Score value object representing a relevance score.

    Immutable value object with validation and comparison operations.
    Scores are typically normalized between 0.0 and 1.0.
    """

    value: float

    def __post_init__(self):
        """Validate score on construction."""
        if not isinstance(self.value, int | float):
            raise TypeError(f"Score must be numeric, got {type(self.value)}")

        if self.value < 0.0:
            raise ValueError(f"Score cannot be negative, got {self.value}")

    def is_above_threshold(self, threshold: float) -> bool:
        """
        Check if score exceeds threshold.

        Args:
            threshold: Minimum threshold value

        Returns:
            True if score >= threshold
        """
        return self.value >= threshold

    def is_below_threshold(self, threshold: float) -> bool:
        """
        Check if score is below threshold.

        Args:
            threshold: Maximum threshold value

        Returns:
            True if score < threshold
        """
        return self.value < threshold

    def is_relevant(self, threshold: float = 0.7) -> bool:
        """
        Check if score indicates relevance.

        Args:
            threshold: Relevance threshold (default: 0.7)

        Returns:
            True if score indicates relevance
        """
        return self.is_above_threshold(threshold)

    def is_highly_relevant(self, threshold: float = 0.85) -> bool:
        """
        Check if score indicates high relevance.

        Args:
            threshold: High relevance threshold (default: 0.85)

        Returns:
            True if score indicates high relevance
        """
        return self.is_above_threshold(threshold)

    def normalized(self, max_value: float = 1.0) -> float:
        """
        Get normalized score (0.0 to 1.0).

        Args:
            max_value: Maximum value for normalization

        Returns:
            Normalized score between 0.0 and 1.0
        """
        if max_value <= 0:
            raise ValueError("max_value must be positive")

        return min(self.value / max_value, 1.0)

    def as_percentage(self) -> float:
        """
        Get score as percentage (0-100).

        Returns:
            Score as percentage
        """
        return self.value * 100.0

    def __float__(self) -> float:
        """Convert to float."""
        return float(self.value)

    def __int__(self) -> int:
        """Convert to int (truncated)."""
        return int(self.value)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.value:.4f}"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"Score({self.value:.4f})"

    def __add__(self, other: Any) -> "Score":
        """Add two scores or a score and a number."""
        if isinstance(other, Score):
            return Score(self.value + other.value)
        if isinstance(other, int | float):
            return Score(self.value + other)
        return NotImplemented

    def __sub__(self, other: Any) -> "Score":
        """Subtract two scores or a score and a number."""
        if isinstance(other, Score):
            return Score(self.value - other.value)
        if isinstance(other, int | float):
            return Score(self.value - other)
        return NotImplemented

    def __mul__(self, other: Any) -> "Score":
        """Multiply score by a number."""
        if isinstance(other, int | float):
            return Score(self.value * other)
        return NotImplemented

    def __truediv__(self, other: Any) -> "Score":
        """Divide score by a number."""
        if isinstance(other, int | float):
            if other == 0:
                raise ZeroDivisionError("Cannot divide score by zero")
            return Score(self.value / other)
        return NotImplemented

    @classmethod
    def from_float(cls, value: float) -> "Score":
        """
        Create Score from float value.

        Args:
            value: Score value

        Returns:
            New Score instance
        """
        return cls(value=float(value))

    @classmethod
    def zero(cls) -> "Score":
        """Create a zero score."""
        return cls(value=0.0)

    @classmethod
    def max(cls) -> "Score":
        """Create a maximum score (1.0)."""
        return cls(value=1.0)
