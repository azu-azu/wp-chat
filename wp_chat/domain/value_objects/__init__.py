"""
Value Objects - Immutable domain values

This module contains value objects:
- Query: Represents a search query with validation
- Score: Represents a relevance score with comparison logic
"""

from .query import Query
from .score import Score

__all__ = [
    "Query",
    "Score",
]
