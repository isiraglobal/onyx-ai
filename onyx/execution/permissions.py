"""Fine-grained permission policies and boundary control."""

from enum import Enum
import os
from pathlib import Path
import re
from typing import Dict, List, Optional, Any
import yaml


class PermissionAction(str, Enum):
    ALLOW = "ALLOW"
    ASK = "ASK"
    DENY = "DENY"


class PermissionManager:
    """Evaluates requested tool executions against security policies."""

    def __init__(self, policy_file: Optional[str] = "configs/permissions.yaml"):
        self.policy_file = policy_file
        self.allowed_roots: List[str] = ["data/workspaces", "data/learning", "data/memory", "configs"]
        self.denied_paths: List[str] = ["/etc", "/var", "/System", "/Library", "~/.ssh", "~/.gnupg", "~/.aws", ".env"]
        self.auto_allowed_commands: List[str] = ["ls", "cat", "head", "tail", "grep", "find", "echo", "pwd", "python3", "pytest", "git", "uname"]
        self.denied_command_patterns: List[str] = [
            r"rm\s+-rf\s+/",
            r"mkfs",
            r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # fork bomb
            r"chmod\s+-R\s+777\s+/",
            r"dd\s+if=",
            r"sudo\s+",
        ]
        self._load_policy()

    def _load_policy(self) -> None:
        if self.policy_file and Path(self.policy_file).exists():
            try:
                with open(self.policy_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                fs = data.get("policies", {}).get("filesystem", {})
                if "allowed_roots" in fs:
                    self.allowed_roots = fs["allowed_roots"]
                if "denied_paths" in fs:
                    self.denied_paths = fs["denied_paths"]

                term = data.get("policies", {}).get("terminal", {})
                if "auto_allowed_commands" in term:
                    self.auto_allowed_commands = term["auto_allowed_commands"]
            except Exception:
                pass

    def evaluate_command(self, cmd: str) -> PermissionAction:
        """Evaluate whether a shell/terminal command is permitted."""
        trimmed = cmd.strip()
        if not trimmed:
            return PermissionAction.DENY

        # 1. Check against explicitly denied dangerous patterns
        for pattern in self.denied_command_patterns:
            if re.search(pattern, trimmed):
                return PermissionAction.DENY

        # 2. Check base command against auto-allowed whitelist
        first_token = trimmed.split()[0]
        base_cmd = os.path.basename(first_token)
        if base_cmd in self.auto_allowed_commands:
            return PermissionAction.ALLOW

        # 3. Default safe policy: ask user for confirmation or sandboxed
        return PermissionAction.ASK

    def evaluate_path_access(self, target_path: str, is_write: bool = False) -> PermissionAction:
        """Evaluate whether filesystem access to a target path is allowed."""
        expanded = str(Path(os.path.expanduser(target_path)).resolve())

        # Check denied sensitive paths
        for denied in self.denied_paths:
            denied_expanded = str(Path(os.path.expanduser(denied)).resolve())
            if expanded.startswith(denied_expanded):
                return PermissionAction.DENY

        # For writing, check that target resides in allowed roots or current working directory
        if is_write:
            cwd = str(Path.cwd().resolve())
            if expanded.startswith(cwd):
                return PermissionAction.ALLOW
            for root in self.allowed_roots:
                root_expanded = str(Path(root).resolve())
                if expanded.startswith(root_expanded):
                    return PermissionAction.ALLOW
            return PermissionAction.ASK

        return PermissionAction.ALLOW
