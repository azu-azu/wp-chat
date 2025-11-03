"""
Domain Models - Core business entities

This module contains the main business entities:
- Document: Represents a searchable document with metadata
- SearchResult: Encapsulates search operation results
- GenerationResult: Encapsulates RAG generation results
"""

from .document import Document
from .generation_result import GenerationResult
from .search_result import SearchResult

__all__ = [
    "Document",
    "SearchResult",
    "GenerationResult",
]
