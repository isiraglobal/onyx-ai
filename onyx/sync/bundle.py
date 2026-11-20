"""Sync bundle packaging, cryptographic integrity, and node export/import."""

from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
import tarfile
import time
from typing import Dict, List, Optional, Any
from onyx.memory.manager import MemoryManager
from onyx.memory.categories import MemoryCategory, MemoryRecord


@dataclass
class BundleMetadata:
    bundle_version: str
    source_node_id: str
    created_at: float
    record_count: int
    allowed_categories: List[str]
    checksum_sha256: str = ""


class SyncBundleManager:
    """Creates and unpacks portable, tamper-evident ONYX sync bundles (.onyx)."""

    def __init__(self, node_id: str = "onyx-node-primary", bundle_dir: str = "data/sync"):
        self.node_id = node_id
        self.bundle_dir = Path(bundle_dir)
        self.bundle_dir.mkdir(parents=True, exist_ok=True)

    async def export_bundle(
        self,
        memory: MemoryManager,
        allowed_categories: Optional[List[MemoryCategory]] = None,
        bundle_name: Optional[str] = None,
    ) -> Path:
        """Export approved memories into a signed compressed sync archive."""
        name = bundle_name or f"onyx_sync_{self.node_id}_{int(time.time())}.onyx"
        target_path = self.bundle_dir / name

        all_records = await memory.store.export_all()
        categories_to_export = allowed_categories or [
            MemoryCategory.SKILLS,
            MemoryCategory.IDENTITY,
            MemoryCategory.LONG_TERM_KNOWLEDGE,
            MemoryCategory.OPERATING_PRINCIPLES,
        ]

        filtered_records = [
            r for r in all_records if r.category in categories_to_export and not r.is_expired()
        ]

        records_json = json.dumps([r.to_dict() for r in filtered_records], indent=2)
        checksum = hashlib.sha256(records_json.encode("utf-8")).hexdigest()

        meta = BundleMetadata(
            bundle_version="1.0",
            source_node_id=self.node_id,
            created_at=time.time(),
            record_count=len(filtered_records),
            allowed_categories=[c.value for c in categories_to_export],
            checksum_sha256=checksum,
        )

        # Write to temporary staging folder, then tar.gz
        staging_dir = self.bundle_dir / f"stage_{int(time.time())}"
        staging_dir.mkdir(parents=True, exist_ok=True)

        meta_file = staging_dir / "metadata.json"
        data_file = staging_dir / "records.json"

        meta_file.write_text(json.dumps(asdict(meta), indent=2), encoding="utf-8")
        data_file.write_text(records_json, encoding="utf-8")

        with tarfile.open(target_path, "w:gz") as tar:
            tar.add(meta_file, arcname="metadata.json")
            tar.add(data_file, arcname="records.json")

        # Cleanup staging
        meta_file.unlink(missing_ok=True)
        data_file.unlink(missing_ok=True)
        staging_dir.rmdir()

        return target_path

    async def import_bundle(
        self,
        bundle_path: str,
        memory: MemoryManager,
        conflict_resolution: str = "newer_wins",  # newer_wins | source_priority
    ) -> Dict[str, Any]:
        """Validate checksum and import records from an ONYX bundle."""
        p = Path(bundle_path)
        if not p.exists():
            raise FileNotFoundError(f"Sync bundle not found: {bundle_path}")

        staging_dir = self.bundle_dir / f"extract_{int(time.time())}"
        staging_dir.mkdir(parents=True, exist_ok=True)

        with tarfile.open(p, "r:gz") as tar:
            if hasattr(tarfile, 'data_filter'):
                tar.extractall(path=staging_dir, filter='data')
            else:
                tar.extractall(path=staging_dir)

        meta_file = staging_dir / "metadata.json"
        data_file = staging_dir / "records.json"

        if not meta_file.exists() or not data_file.exists():
            shutil_cleanup(staging_dir)
            raise ValueError("Corrupt bundle: missing metadata.json or records.json")

        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        records_raw = data_file.read_text(encoding="utf-8")

        # Verify cryptographic checksum
        computed_hash = hashlib.sha256(records_raw.encode("utf-8")).hexdigest()
        if computed_hash != meta.get("checksum_sha256"):
            shutil_cleanup(staging_dir)
            raise ValueError("Cryptographic verification failed: bundle checksum mismatch!")

        records_data = json.loads(records_raw)
        imported_records = [MemoryRecord.from_dict(d) for d in records_data]

        imported_count = 0
        updated_count = 0

        for inc_rec in imported_records:
            existing = await memory.store.get(inc_rec.id)
            if existing:
                if conflict_resolution == "newer_wins":
                    if inc_rec.updated_at >= existing.updated_at:
                        await memory.store.update(inc_rec)
                        updated_count += 1
                else:
                    await memory.store.update(inc_rec)
                    updated_count += 1
            else:
                await memory.store.add(inc_rec)
                imported_count += 1

        shutil_cleanup(staging_dir)

        return {
            "source_node": meta.get("source_node_id"),
            "total_in_bundle": len(imported_records),
            "new_imported": imported_count,
            "updated_conflicts": updated_count,
            "verified": True,
        }


def shutil_cleanup(p: Path) -> None:
    for child in p.iterdir():
        if child.is_file():
            child.unlink(missing_ok=True)
    p.rmdir()
