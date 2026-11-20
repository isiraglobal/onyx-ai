"""Personal memory categories and record data models."""

from dataclasses import dataclass, field, asdict
from enum import Enum
import time
from typing import Dict, List, Optional, Any
import uuid


class MemoryCategory(str, Enum):
    IDENTITY = "identity"                     # User preferences, system identity
    OPERATING_PRINCIPLES = "principles"       # Operating instructions, safety rules
    LONG_TERM_KNOWLEDGE = "knowledge"         # Distilled facts, reference information
    EPISODIC = "episodic"                     # Previous task runs, outcomes, history
    SKILLS = "skills"                         # Learned procedures, tool recipes
    PROJECTS = "projects"                     # Active project states, requirements
    FEEDBACK = "feedback"                     # User corrections, reviews, ratings
    TEMPORARY = "temporary"                   # Ephemeral conversation state with TTL


@dataclass
class MemoryRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: MemoryCategory = MemoryCategory.LONG_TERM_KNOWLEDGE
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    confidence: float = 1.0                   # 0.0 to 1.0 confidence score
    source: str = "user"                      # Source origin: user, agent, doc, system
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None        # Unix timestamp for auto-expiration

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        if self.expires_at is None:
            return False
        now = current_time or time.time()
        return now >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRecord":
        cat = data.get("category", MemoryCategory.LONG_TERM_KNOWLEDGE.value)
        if isinstance(cat, str):
            cat = MemoryCategory(cat)
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            category=cat,
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
            confidence=float(data.get("confidence", 1.0)),
            source=data.get("source", "user"),
            created_at=float(data.get("created_at", time.time())),
            updated_at=float(data.get("updated_at", time.time())),
            expires_at=data.get("expires_at"),
        )
