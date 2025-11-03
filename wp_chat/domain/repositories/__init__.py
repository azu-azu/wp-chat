"""
Repository Interfaces - Abstract data access contracts

This module contains repository interfaces following the Repository Pattern:
- SearchRepository: Interface for search operations
- CacheRepository: Interface for caching operations

These interfaces define contracts that infrastructure layer must implement,
ensuring the domain layer remains independent of specific technologies.
"""

from .cache_repository import CacheRepository
from .search_repository import SearchRepository

__all__ = [
    "SearchRepository",
    "CacheRepository",
]
