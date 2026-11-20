"""Embedded SQLite memory store with vector search and metadata filtering."""

import json
from pathlib import Path
import sqlite3
import time
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from onyx.memory.base import MemoryStore
from onyx.memory.categories import MemoryCategory, MemoryRecord
from onyx.memory.embeddings import cosine_similarity


class SQLiteMemoryStore(MemoryStore):
    """Local embedded SQLite storage with indexed metadata and vectorized cosine search."""

    def __init__(self, db_path: str = "data/memory/onyx_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            with self._conn:
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS memory_records (
                        id TEXT PRIMARY KEY,
                        category TEXT NOT NULL,
                        content TEXT NOT NULL,
                        metadata_json TEXT NOT NULL,
                        embedding_blob BLOB,
                        confidence REAL NOT NULL DEFAULT 1.0,
                        source TEXT NOT NULL DEFAULT 'user',
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        expires_at REAL
                    )
                """)
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_category ON memory_records(category)")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_expires ON memory_records(expires_at)")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_confidence ON memory_records(confidence)")
        return self._conn

    async def initialize(self) -> None:
        conn = self._get_conn()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_records (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    embedding_blob BLOB,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    source TEXT NOT NULL DEFAULT 'user',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    expires_at REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_category ON memory_records(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_expires ON memory_records(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_confidence ON memory_records(confidence)")

    async def add(self, record: MemoryRecord) -> str:
        conn = self._get_conn()
        emb_blob = None
        if record.embedding:
            emb_blob = np.array(record.embedding, dtype=np.float32).tobytes()

        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_records 
                (id, category, content, metadata_json, embedding_blob, confidence, source, created_at, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.category.value,
                    record.content,
                    json.dumps(record.metadata),
                    emb_blob,
                    record.confidence,
                    record.source,
                    record.created_at,
                    record.updated_at,
                    record.expires_at,
                ),
            )
        return record.id

    async def get(self, record_id: str) -> Optional[MemoryRecord]:
        conn = self._get_conn()
        cur = conn.execute("SELECT * FROM memory_records WHERE id = ?", (record_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    async def update(self, record: MemoryRecord) -> bool:
        record.updated_at = time.time()
        await self.add(record)
        return True

    async def delete(self, record_id: str) -> bool:
        conn = self._get_conn()
        with conn:
            cur = conn.execute("DELETE FROM memory_records WHERE id = ?", (record_id,))
            return cur.rowcount > 0

    async def search_semantic(
        self,
        query_embedding: List[float],
        category: Optional[MemoryCategory] = None,
        limit: int = 10,
        min_confidence: float = 0.0,
    ) -> List[Tuple[MemoryRecord, float]]:
        conn = self._get_conn()
        now = time.time()

        query = "SELECT * FROM memory_records WHERE (expires_at IS NULL OR expires_at > ?) AND confidence >= ?"
        params: List[Any] = [now, min_confidence]

        if category:
            query += " AND category = ?"
            params.append(category.value)

        cur = conn.execute(query, tuple(params))
        rows = cur.fetchall()

        scored: List[Tuple[MemoryRecord, float]] = []
        for row in rows:
            record = self._row_to_record(row)
            if record.embedding:
                score = cosine_similarity(query_embedding, record.embedding)
                scored.append((record, score))

        # Sort descending by similarity score
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    async def filter_metadata(
        self,
        category: Optional[MemoryCategory] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
    ) -> List[MemoryRecord]:
        conn = self._get_conn()
        now = time.time()
        query = "SELECT * FROM memory_records WHERE (expires_at IS NULL OR expires_at > ?)"
        params: List[Any] = [now]

        if category:
            query += " AND category = ?"
            params.append(category.value)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit * 2)  # Overfetch slightly for Python-side JSON filtering

        cur = conn.execute(query, tuple(params))
        rows = cur.fetchall()

        results: List[MemoryRecord] = []
        for row in rows:
            rec = self._row_to_record(row)
            if metadata_filters:
                match = True
                for k, v in metadata_filters.items():
                    if rec.metadata.get(k) != v:
                        match = False
                        break
                if not match:
                    continue
            results.append(rec)
            if len(results) >= limit:
                break
        return results

    async def purge_expired(self) -> int:
        conn = self._get_conn()
        now = time.time()
        with conn:
            cur = conn.execute("DELETE FROM memory_records WHERE expires_at IS NOT NULL AND expires_at <= ?", (now,))
            return cur.rowcount

    async def export_all(self) -> List[MemoryRecord]:
        conn = self._get_conn()
        cur = conn.execute("SELECT * FROM memory_records ORDER BY created_at ASC")
        return [self._row_to_record(r) for r in cur.fetchall()]

    async def import_all(self, records: List[MemoryRecord]) -> int:
        count = 0
        for rec in records:
            await self.add(rec)
            count += 1
        return count

    async def clear(self) -> None:
        conn = self._get_conn()
        with conn:
            conn.execute("DELETE FROM memory_records")

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        emb = None
        if row["embedding_blob"]:
            emb = np.frombuffer(row["embedding_blob"], dtype=np.float32).tolist()

        return MemoryRecord(
            id=row["id"],
            category=MemoryCategory(row["category"]),
            content=row["content"],
            metadata=json.loads(row["metadata_json"]),
            embedding=emb,
            confidence=row["confidence"],
            source=row["source"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            expires_at=row["expires_at"],
        )
