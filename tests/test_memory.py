"""Unit tests for ONYX personal memory system."""

import os
import tempfile
import time
import pytest
from onyx.memory.categories import MemoryCategory, MemoryRecord
from onyx.memory.embeddings import LocalEmbeddingProvider, cosine_similarity
from onyx.memory.sqlite_store import SQLiteMemoryStore
from onyx.memory.manager import MemoryManager


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.mark.asyncio
async def test_memory_record_and_expiration():
    rec = MemoryRecord(
        category=MemoryCategory.TEMPORARY,
        content="Short lived session fact",
        expires_at=time.time() - 10,
    )
    assert rec.is_expired() is True

    valid_rec = MemoryRecord(
        category=MemoryCategory.LONG_TERM_KNOWLEDGE,
        content="Permanent architecture decision",
        expires_at=time.time() + 3600,
    )
    assert valid_rec.is_expired() is False

    d = valid_rec.to_dict()
    assert d["category"] == "knowledge"
    restored = MemoryRecord.from_dict(d)
    assert restored.content == valid_rec.content
    assert restored.category == MemoryCategory.LONG_TERM_KNOWLEDGE


@pytest.mark.asyncio
async def test_sqlite_memory_store_crud(temp_db_path):
    store = SQLiteMemoryStore(db_path=temp_db_path)
    await store.initialize()

    embedder = LocalEmbeddingProvider()
    emb = embedder.embed_text("ONYX is a portable personal intelligence.")

    record = MemoryRecord(
        category=MemoryCategory.IDENTITY,
        content="Name is ONYX, developed for owner Lakshit.",
        metadata={"priority": "high", "topic": "identity"},
        embedding=emb,
    )

    # 1. Add
    rec_id = await store.add(record)
    assert rec_id == record.id

    # 2. Get
    fetched = await store.get(rec_id)
    assert fetched is not None
    assert fetched.content == record.content
    assert fetched.metadata["priority"] == "high"

    # 3. Filter metadata
    filtered = await store.filter_metadata(
        category=MemoryCategory.IDENTITY,
        metadata_filters={"priority": "high"},
    )
    assert len(filtered) == 1
    assert filtered[0].id == rec_id

    # 4. Semantic search
    search_results = await store.search_semantic(emb, category=MemoryCategory.IDENTITY, limit=5)
    assert len(search_results) == 1
    rec_found, score = search_results[0]
    assert rec_found.id == rec_id
    assert score > 0.99  # Identical text should have ~1.0 cosine similarity

    # 5. Delete
    deleted = await store.delete(rec_id)
    assert deleted is True
    assert await store.get(rec_id) is None


@pytest.mark.asyncio
async def test_memory_manager_deduplication_and_recall(temp_db_path):
    manager = MemoryManager(db_path=temp_db_path, dedup_threshold=0.90)
    await manager.initialize()

    # Remember fact
    rec1 = await manager.remember(
        content="The server runs on port 8080 by default.",
        category=MemoryCategory.SKILLS,
        metadata={"module": "network"},
    )

    # Remember virtually identical fact -> should deduplicate / update
    rec2 = await manager.remember(
        content="The server runs on port 8080 by default.",
        category=MemoryCategory.SKILLS,
        metadata={"module": "network", "updated": True},
    )
    assert rec1.id == rec2.id
    assert rec2.metadata.get("updated") is True

    # Recall
    recalled = await manager.recall("What port does the server run on?")
    assert len(recalled) >= 1
    assert "8080" in recalled[0][0].content

    # Context block
    context = await manager.get_context_block("port config")
    assert "8080" in context


@pytest.mark.asyncio
async def test_memory_backup_and_restore(temp_db_path):
    manager = MemoryManager(db_path=temp_db_path)
    await manager.initialize()

    await manager.remember("Principle: Prioritize local execution.", MemoryCategory.OPERATING_PRINCIPLES)
    await manager.remember("Docker is installed at /usr/local/bin/docker.", MemoryCategory.LONG_TERM_KNOWLEDGE)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        backup_file = f.name

    try:
        exported_path = await manager.backup(backup_file)
        assert os.path.exists(exported_path)

        # Clear store and restore
        await manager.store.clear()
        recalled_empty = await manager.recall("Docker")
        assert len(recalled_empty) == 0

        restored_count = await manager.restore(exported_path)
        assert restored_count == 2

        recalled_after = await manager.recall("Docker")
        assert len(recalled_after) == 1
        assert "docker" in recalled_after[0][0].content.lower()
    finally:
        if os.path.exists(backup_file):
            os.remove(backup_file)


@pytest.mark.asyncio
async def test_postgres_memory_store_interface():
    from onyx.memory.postgres_store import PostgresMemoryStore
    pg_store = PostgresMemoryStore(pg_url="postgresql://invalid_user:invalid_pass@localhost:5432/invalid_db")
    # Verify proper error handling when db is unreachable
    with pytest.raises(Exception):
        await pg_store.initialize()

