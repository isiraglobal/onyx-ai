"""Unit tests for ONYX sync bundles and conflict resolution."""

import os
import shutil
import tempfile
import time
import pytest
from onyx.memory.manager import MemoryManager
from onyx.memory.categories import MemoryCategory
from onyx.sync.bundle import SyncBundleManager


@pytest.fixture
def sync_env():
    temp_dir = tempfile.mkdtemp(prefix="onyx_sync_test_")
    db1 = os.path.join(temp_dir, "node1_mem.db")
    db2 = os.path.join(temp_dir, "node2_mem.db")
    bundle_dir = os.path.join(temp_dir, "bundles")

    mem1 = MemoryManager(db_path=db1)
    mem2 = MemoryManager(db_path=db2)

    yield temp_dir, mem1, mem2, bundle_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_bundle_export_and_import(sync_env):
    temp_dir, mem1, mem2, bundle_dir = sync_env
    await mem1.initialize()
    await mem2.initialize()

    # Add records on Node 1
    rec1 = await mem1.remember("Skill: python -m venv .venv", MemoryCategory.SKILLS)
    rec2 = await mem1.remember("Identity: Personal AI for Lakshit", MemoryCategory.IDENTITY)

    mgr1 = SyncBundleManager(node_id="node-1", bundle_dir=bundle_dir)
    bundle_path = await mgr1.export_bundle(mem1)

    assert os.path.exists(bundle_path)
    assert str(bundle_path).endswith(".onyx")

    # Import into Node 2
    mgr2 = SyncBundleManager(node_id="node-2", bundle_dir=bundle_dir)
    res = await mgr2.import_bundle(str(bundle_path), mem2)

    assert res["verified"] is True
    assert res["new_imported"] == 2
    assert res["source_node"] == "node-1"

    # Verify records present in Node 2
    recalled = await mem2.recall("venv")
    assert len(recalled) >= 1
    assert "venv" in recalled[0][0].content


@pytest.mark.asyncio
async def test_sync_conflict_resolution(sync_env):
    temp_dir, mem1, mem2, bundle_dir = sync_env
    await mem1.initialize()
    await mem2.initialize()

    # Create record on Node 1
    rec1 = await mem1.remember("Initial configuration port 8080", MemoryCategory.SKILLS)

    mgr1 = SyncBundleManager(node_id="node-1", bundle_dir=bundle_dir)
    bundle1 = await mgr1.export_bundle(mem1)

    # Import into Node 2
    mgr2 = SyncBundleManager(node_id="node-2", bundle_dir=bundle_dir)
    await mgr2.import_bundle(str(bundle1), mem2)

    # Now update record on Node 1 with newer timestamp
    time.sleep(0.01)
    rec1.content = "Updated configuration port 9090"
    rec1.updated_at = time.time() + 10.0
    await mem1.store.update(rec1)

    bundle2 = await mgr1.export_bundle(mem1)
    res2 = await mgr2.import_bundle(str(bundle2), mem2, conflict_resolution="newer_wins")

    assert res2["updated_conflicts"] == 1
    node2_rec = await mem2.store.get(rec1.id)
    assert "9090" in node2_rec.content
