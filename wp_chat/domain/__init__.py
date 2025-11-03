"""
Domain Layer - Business logic and domain models

This layer contains:
- Domain models: Core business entities
- Repositories: Abstract interfaces for data access
- Value objects: Immutable domain values

Following Clean Architecture principles:
- Independent of frameworks and external libraries
- Independent of infrastructure (FAISS, Redis, etc.)
- Testable without external dependencies
"""

from .models.document import Document
from .models.generation_result import GenerationResult
from .models.search_result import SearchResult
from .repositories.cache_repository import CacheRepository
from .repositories.search_repository import SearchRepository
from .value_objects.query import Query
from .value_objects.score import Score

__all__ = [
    "Document",
    "SearchResult",
    "GenerationResult",
    "Query",
    "Score",
    "SearchRepository",
    "CacheRepository",
]
