"""Security authentication and audit logging."""

from dataclasses import dataclass, asdict
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Dict, List, Optional, Any


@dataclass
class AuditEntry:
    timestamp: float
    actor: str
    action: str
    target: str
    status: str
    details: Dict[str, Any]
    entry_hash: str = ""

    def compute_hash(self, prev_hash: str = "") -> str:
        payload = f"{self.timestamp}:{self.actor}:{self.action}:{self.target}:{self.status}:{prev_hash}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditLogger:
    """Tamper-evident hash-chained audit log for all system and tool operations."""

    def __init__(self, log_path: str = "data/security/audit.log"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_hash = ""
        self._init_chain()

    def _init_chain(self) -> None:
        if self.log_path.exists() and self.log_path.stat().st_size > 0:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            item = json.loads(line.strip())
                            self.last_hash = item.get("entry_hash", "")
                        except Exception:
                            pass

    def log(self, actor: str, action: str, target: str, status: str = "SUCCESS", details: Optional[Dict[str, Any]] = None) -> AuditEntry:
        entry = AuditEntry(
            timestamp=time.time(),
            actor=actor,
            action=action,
            target=target,
            status=status,
            details=details or {},
        )
        entry.entry_hash = entry.compute_hash(self.last_hash)
        self.last_hash = entry.entry_hash

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

        return entry

    def verify_integrity(self) -> bool:
        """Verify hash chain integrity across all entries in the audit log."""
        if not self.log_path.exists():
            return True

        current_prev = ""
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line.strip())
                expected_hash = item.get("entry_hash")
                entry = AuditEntry(
                    timestamp=item["timestamp"],
                    actor=item["actor"],
                    action=item["action"],
                    target=item["target"],
                    status=item["status"],
                    details=item.get("details", {}),
                )
                computed = entry.compute_hash(current_prev)
                if computed != expected_hash:
                    return False
                current_prev = computed

        return True


def verify_auth_token(token: Optional[str], expected_token: Optional[str]) -> bool:
    """Validate bearer token against configured secret."""
    if not expected_token:
        return True  # Auth not required
    return token == expected_token
