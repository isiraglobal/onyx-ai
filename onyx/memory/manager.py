"""Central memory coordinator providing semantic retrieval, deduplication, and backup/restore."""

import gzip
import json
from pathlib import Path
import time
from typing import Dict, List, Optional, Any, Tuple
from onyx.memory.base import MemoryStore
from onyx.memory.categories import MemoryCategory, MemoryRecord
from onyx.memory.embeddings import LocalEmbeddingProvider, cosine_similarity
from onyx.memory.sqlite_store import SQLiteMemoryStore


class MemoryManager:
    """Orchestrates structured memory operations, deduplication, and context retrieval."""

    def __init__(
        self,
        store: Optional[MemoryStore] = None,
        embedding_provider: Optional[LocalEmbeddingProvider] = None,
        db_path: str = "data/memory/onyx_memory.db",
        dedup_threshold: float = 0.92,
    ):
        self.store = store or SQLiteMemoryStore(db_path=db_path)
        self.embedder = embedding_provider or LocalEmbeddingProvider()
        self.dedup_threshold = dedup_threshold

    async def initialize(self) -> None:
        """Initialize underlying storage schema."""
        await self.store.initialize()

    async def remember(
        self,
        content: str,
        category: MemoryCategory = MemoryCategory.LONG_TERM_KNOWLEDGE,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "user",
        confidence: float = 1.0,
        ttl_seconds: Optional[int] = None,
    ) -> MemoryRecord:
        """Store a new memory item, checking for deduplication first."""
        cleaned = content.strip()
        if not cleaned:
            raise ValueError("Memory content cannot be empty.")

        embedding = self.embedder.embed_text(cleaned)
        expires_at = (time.time() + ttl_seconds) if ttl_seconds else None

        # Check for near-identical duplicate within category
        existing = await self.store.search_semantic(
            query_embedding=embedding,
            category=category,
            limit=1,
            min_confidence=0.0,
        )

        if existing and existing[0][1] >= self.dedup_threshold:
            # Update existing record
            existing_rec, score = existing[0]
            existing_rec.content = cleaned
            existing_rec.confidence = max(existing_rec.confidence, confidence)
            existing_rec.updated_at = time.time()
            if metadata:
                existing_rec.metadata.update(metadata)
            if expires_at:
                existing_rec.expires_at = expires_at
            await self.store.update(existing_rec)
            return existing_rec

        # Otherwise create new record
        record = MemoryRecord(
            category=category,
            content=cleaned,
            metadata=metadata or {},
            embedding=embedding,
            confidence=confidence,
            source=source,
            expires_at=expires_at,
        )
        await self.store.add(record)
        return record

    async def recall(
        self,
        query: str,
        category: Optional[MemoryCategory] = None,
        limit: int = 5,
        min_similarity: float = 0.10,
    ) -> List[Tuple[MemoryRecord, float]]:
        """Retrieve relevant memories matching a query string."""
        query_emb = self.embedder.embed_text(query)
        results = await self.store.search_semantic(
            query_embedding=query_emb,
            category=category,
            limit=limit,
        )
        return [(rec, score) for rec, score in results if score >= min_similarity]

    async def get_context_block(self, query: str, limit_per_category: int = 4) -> str:
        """Synthesize a unified, highly focused context block from core books and memory."""
        lines: List[str] = []
        q_lower = query.lower()

        # Direct doctrinal keyword matching for maximum precision
        is_qla = any(w in q_lower for w in ["qla", "step", "acquisition", "board", "opm", "business idea", "quantum", "roll-up", "rollup"])
        is_htc = any(w in q_lower for w in ["closing", "close", "client", "objection", "think about it", "sales", "price", "pitch", "doctor"])

        # 1. Identity & System Foundation
        identities = await self.store.filter_metadata(category=MemoryCategory.IDENTITY)
        if identities:
            lines.append("### Operating Principles & Identity:")
            for ident in identities[:2]:
                lines.append(f"{ident.content.strip()}\n")

        # 2. Targeted Retrieval for QLA & Knowledge
        query_emb = self.embedder.embed_text(query)
        knowledge_results = await self.store.search_semantic(
            query_embedding=query_emb,
            category=MemoryCategory.LONG_TERM_KNOWLEDGE,
            limit=limit_per_category * 2,
            min_confidence=0.0,
        )

        selected_knowledge = []
        for k, score in knowledge_results:
            if is_qla and ("qla" in k.source or "11 steps" in k.content.lower() or "quantum leap" in k.content.lower()):
                selected_knowledge.append((k, score + 0.5))
            elif score >= 0.12:
                selected_knowledge.append((k, score))

        selected_knowledge.sort(key=lambda x: x[1], reverse=True)
        if selected_knowledge:
            lines.append("### Ground Truth Doctrine (Quantum Leap Advantage / QLA):")
            for k, _ in selected_knowledge[:limit_per_category]:
                lines.append(f"{k.content.strip()}\n")

        # 3. Targeted Retrieval for High Ticket Closing (HTC) Sales Skills
        skills_results = await self.store.search_semantic(
            query_embedding=query_emb,
            category=MemoryCategory.SKILLS,
            limit=limit_per_category * 2,
            min_confidence=0.0,
        )

        selected_skills = []
        for s, score in skills_results:
            if is_htc and ("dan_lok" in s.source or "think about it" in s.content.lower() or "closer" in s.content.lower()):
                selected_skills.append((s, score + 0.5))
            elif score >= 0.12:
                selected_skills.append((s, score))

        selected_skills.sort(key=lambda x: x[1], reverse=True)
        if selected_skills:
            lines.append("### Sales Execution & Tactical Frameworks (Dan Lok HTC):")
            for s, _ in selected_skills[:limit_per_category]:
                lines.append(f"{s.content.strip()}\n")

        # 4. Active Projects & Obsidian Connections
        project_results = await self.store.search_semantic(
            query_embedding=query_emb,
            category=MemoryCategory.PROJECTS,
            limit=limit_per_category,
            min_confidence=0.0,
        )
        if project_results:
            lines.append("### Active Business Ventures & Connections (Obsidian):")
            for p, score in project_results:
                if score >= 0.10:
                    lines.append(f"{p.content.strip()}\n")

        return "\n".join(lines)

    async def purge_expired(self) -> int:
        """Clean up expired temporary records."""
        return await self.store.purge_expired()

    async def backup(self, output_path: str) -> str:
        """Export all memories to a timestamped compressed JSON file."""
        records = await self.store.export_all()
        data = {
            "version": "1.0",
            "exported_at": time.time(),
            "count": len(records),
            "records": [r.to_dict() for r in records],
        }
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if str(output_path).endswith(".gz"):
            with gzip.open(p, "wt", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        else:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        return str(p)

    async def restore(self, input_path: str, clear_existing: bool = False) -> int:
        """Restore memories from a JSON or gzipped backup file."""
        p = Path(input_path)
        if not p.exists():
            raise FileNotFoundError(f"Backup file not found: {input_path}")

        if str(input_path).endswith(".gz"):
            with gzip.open(p, "rt", encoding="utf-8") as f:
                data = json.load(f)
        else:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)

        records_data = data.get("records", [])
        records = [MemoryRecord.from_dict(d) for d in records_data]

        if clear_existing:
            await self.store.clear()

        return await self.store.import_all(records)
