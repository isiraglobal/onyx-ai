"""PostgreSQL + pgvector enterprise memory store adapter."""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from onyx.memory.base import MemoryStore
from onyx.memory.categories import MemoryCategory, MemoryRecord
from onyx.memory.embeddings import cosine_similarity


class PostgresMemoryStore(MemoryStore):
    """PostgreSQL storage adapter with pgvector extension support."""

    def __init__(self, pg_url: str = "postgresql://onyx:onyx@localhost:5432/onyx_memory", dimension: int = 384):
        self.pg_url = pg_url
        self.dimension = dimension
        self.pool = None
        self.has_pgvector = False

    async def initialize(self) -> None:
        try:
            import asyncpg
            self.pool = await asyncpg.create_pool(dsn=self.pg_url)
            async with self.pool.acquire() as conn:
                # Try creating pgvector extension
                try:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    self.has_pgvector = True
                except Exception:
                    self.has_pgvector = False

                if self.has_pgvector:
                    await conn.execute(f"""
                        CREATE TABLE IF NOT EXISTS memory_records (
                            id TEXT PRIMARY KEY,
                            category TEXT NOT NULL,
                            content TEXT NOT NULL,
                            metadata_json JSONB NOT NULL,
                            embedding vector({self.dimension}),
                            confidence REAL NOT NULL DEFAULT 1.0,
                            source TEXT NOT NULL DEFAULT 'user',
                            created_at DOUBLE PRECISION NOT NULL,
                            updated_at DOUBLE PRECISION NOT NULL,
                            expires_at DOUBLE PRECISION
                        )
                    """)
                    await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_category ON memory_records(category)")
                    await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_expires ON memory_records(expires_at)")
                else:
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS memory_records (
                            id TEXT PRIMARY KEY,
                            category TEXT NOT NULL,
                            content TEXT NOT NULL,
                            metadata_json JSONB NOT NULL,
                            embedding REAL[],
                            confidence REAL NOT NULL DEFAULT 1.0,
                            source TEXT NOT NULL DEFAULT 'user',
                            created_at DOUBLE PRECISION NOT NULL,
                            updated_at DOUBLE PRECISION NOT NULL,
                            expires_at DOUBLE PRECISION
                        )
                    """)
        except ImportError:
            raise RuntimeError("asyncpg is required for PostgresMemoryStore. Install with: pip install asyncpg")

    async def add(self, record: MemoryRecord) -> str:
        if not self.pool:
            raise RuntimeError("PostgresMemoryStore is not initialized.")

        emb_str = None
        if record.embedding:
            emb_str = f"[{','.join(str(x) for x in record.embedding)}]" if self.has_pgvector else record.embedding

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO memory_records 
                (id, category, content, metadata_json, embedding, confidence, source, created_at, updated_at, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (id) DO UPDATE SET
                    category = EXCLUDED.category,
                    content = EXCLUDED.content,
                    metadata_json = EXCLUDED.metadata_json,
                    embedding = EXCLUDED.embedding,
                    confidence = EXCLUDED.confidence,
                    source = EXCLUDED.source,
                    updated_at = EXCLUDED.updated_at,
                    expires_at = EXCLUDED.expires_at
                """,
                record.id,
                record.category.value,
                record.content,
                json.dumps(record.metadata),
                emb_str,
                record.confidence,
                record.source,
                record.created_at,
                record.updated_at,
                record.expires_at,
            )
        return record.id

    async def get(self, record_id: str) -> Optional[MemoryRecord]:
        if not self.pool:
            raise RuntimeError("PostgresMemoryStore is not initialized.")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM memory_records WHERE id = $1", record_id)
            if not row:
                return None
            return self._row_to_record(row)

    async def update(self, record: MemoryRecord) -> bool:
        record.updated_at = time.time()
        await self.add(record)
        return True

    async def delete(self, record_id: str) -> bool:
        if not self.pool:
            raise RuntimeError("PostgresMemoryStore is not initialized.")
        async with self.pool.acquire() as conn:
            res = await conn.execute("DELETE FROM memory_records WHERE id = $1", record_id)
            return "DELETE 1" in res

    async def search_semantic(
        self,
        query_embedding: List[float],
        category: Optional[MemoryCategory] = None,
        limit: int = 10,
        min_confidence: float = 0.0,
    ) -> List[Tuple[MemoryRecord, float]]:
        if not self.pool:
            raise RuntimeError("PostgresMemoryStore is not initialized.")

        now = time.time()
        async with self.pool.acquire() as conn:
            if self.has_pgvector:
                emb_str = f"[{','.join(str(x) for x in query_embedding)}]"
                query = """
                    SELECT *, (1 - (embedding <=> $1)) AS similarity
                    FROM memory_records
                    WHERE (expires_at IS NULL OR expires_at > $2)
                      AND confidence >= $3
                """
                params = [emb_str, now, min_confidence]
                if category:
                    query += " AND category = $4"
                    params.append(category.value)
                query += " ORDER BY similarity DESC LIMIT " + str(limit)
                rows = await conn.fetch(query, *params)
                return [(self._row_to_record(r), float(r["similarity"])) for r in rows]
            else:
                # In-memory cosine calculation fallback
                query = "SELECT * FROM memory_records WHERE (expires_at IS NULL OR expires_at > $1) AND confidence >= $2"
                params = [now, min_confidence]
                if category:
                    query += " AND category = $3"
                    params.append(category.value)
                rows = await conn.fetch(query, *params)
                scored = []
                for r in rows:
                    rec = self._row_to_record(r)
                    if rec.embedding:
                        scored.append((rec, cosine_similarity(query_embedding, rec.embedding)))
                scored.sort(key=lambda x: x[1], reverse=True)
                return scored[:limit]

    async def filter_metadata(
        self,
        category: Optional[MemoryCategory] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
    ) -> List[MemoryRecord]:
        if not self.pool:
            raise RuntimeError("PostgresMemoryStore is not initialized.")

        now = time.time()
        query = "SELECT * FROM memory_records WHERE (expires_at IS NULL OR expires_at > $1)"
        params = [now]
        if category:
            query += " AND category = $2"
            params.append(category.value)

        query += " ORDER BY updated_at DESC LIMIT " + str(limit * 2)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            results = []
            for r in rows:
                rec = self._row_to_record(r)
                if metadata_filters:
                    match = all(rec.metadata.get(k) == v for k, v in metadata_filters.items())
                    if not match:
                        continue
                results.append(rec)
                if len(results) >= limit:
                    break
            return results

    async def purge_expired(self) -> int:
        if not self.pool:
            raise RuntimeError("PostgresMemoryStore is not initialized.")
        async with self.pool.acquire() as conn:
            res = await conn.execute(
                "DELETE FROM memory_records WHERE expires_at IS NOT NULL AND expires_at <= $1",
                time.time(),
            )
            return int(res.split()[-1])

    async def export_all(self) -> List[MemoryRecord]:
        if not self.pool:
            raise RuntimeError("PostgresMemoryStore is not initialized.")
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM memory_records ORDER BY created_at ASC")
            return [self._row_to_record(r) for r in rows]

    async def import_all(self, records: List[MemoryRecord]) -> int:
        count = 0
        for rec in records:
            await self.add(rec)
            count += 1
        return count

    async def clear(self) -> None:
        if not self.pool:
            return
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM memory_records")

    def _row_to_record(self, row: Any) -> MemoryRecord:
        meta = row["metadata_json"]
        if isinstance(meta, str):
            meta = json.loads(meta)

        emb = row["embedding"]
        if isinstance(emb, str):
            emb = [float(x) for x in emb.strip("[]").split(",") if x.strip()]

        return MemoryRecord(
            id=row["id"],
            category=MemoryCategory(row["category"]),
            content=row["content"],
            metadata=meta,
            embedding=emb,
            confidence=row["confidence"],
            source=row["source"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            expires_at=row["expires_at"],
        )
