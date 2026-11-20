"""Node synchronization engine coordinating peer-to-peer and file-based state transfers."""

from pathlib import Path
from typing import Dict, List, Optional, Any
from onyx.memory.manager import MemoryManager
from onyx.sync.bundle import SyncBundleManager


class SyncEngine:
    """Coordinates node state exchange, integrity checks, and synchronization schedules."""

    def __init__(
        self,
        node_id: str = "onyx-node-primary",
        sync_dir: str = "data/sync",
        memory: Optional[MemoryManager] = None,
    ):
        self.node_id = node_id
        self.memory = memory
        self.bundle_manager = SyncBundleManager(node_id=node_id, bundle_dir=sync_dir)

    async def create_sync_export(self, bundle_name: Optional[str] = None) -> Path:
        if not self.memory:
            raise RuntimeError("MemoryManager required for sync export.")
        return await self.bundle_manager.export_bundle(self.memory, bundle_name=bundle_name)

    async def apply_sync_import(self, bundle_path: str) -> Dict[str, Any]:
        if not self.memory:
            raise RuntimeError("MemoryManager required for sync import.")
        return await self.bundle_manager.import_bundle(bundle_path, self.memory)

    def list_available_bundles(self) -> List[Dict[str, Any]]:
        p = self.bundle_manager.bundle_dir
        if not p.exists():
            return []
        items = []
        for f in sorted(p.glob("*.onyx")):
            items.append({
                "file_name": f.name,
                "file_path": str(f),
                "size_bytes": f.stat().st_size,
                "modified": f.stat().st_mtime,
            })
        return items
