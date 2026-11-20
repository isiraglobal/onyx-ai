"""Abstract base interface for personal memory persistence engines."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from onyx.memory.categories import MemoryCategory, MemoryRecord


class MemoryStore(ABC):
    """Abstract interface for structured and semantic memory storage engines."""

    @abstractmethod
    async def initialize(self) -> None:
        """Create tables, indexes, and connection pools."""
        pass

    @abstractmethod
    async def add(self, record: MemoryRecord) -> str:
        """Insert a new memory record and return its ID."""
        pass

    @abstractmethod
    async def get(self, record_id: str) -> Optional[MemoryRecord]:
        """Retrieve a specific record by ID."""
        pass

    @abstractmethod
    async def update(self, record: MemoryRecord) -> bool:
        """Update an existing memory record."""
        pass

    @abstractmethod
    async def delete(self, record_id: str) -> bool:
        """Delete a memory record by ID."""
        pass

    @abstractmethod
    async def search_semantic(
        self,
        query_embedding: List[float],
        category: Optional[MemoryCategory] = None,
        limit: int = 10,
        min_confidence: float = 0.0,
    ) -> List[Tuple[MemoryRecord, float]]:
        """Search memory by vector cosine similarity, returning (record, similarity_score)."""
        pass

    @abstractmethod
    async def filter_metadata(
        self,
        category: Optional[MemoryCategory] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
    ) -> List[MemoryRecord]:
        """Filter memory records by category and metadata keys."""
        pass

    @abstractmethod
    async def purge_expired(self) -> int:
        """Remove temporary memories whose expires_at timestamp has passed."""
        pass

    @abstractmethod
    async def export_all(self) -> List[MemoryRecord]:
        """Export all non-expired memory records."""
        pass

    @abstractmethod
    async def import_all(self, records: List[MemoryRecord]) -> int:
        """Import a batch of memory records with upsert behavior."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Erase all records (used for test teardown and full resets)."""
        pass
