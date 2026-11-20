"""Obsidian vault integration and bidirectional connection synchronization."""

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import time
from typing import Dict, List, Optional, Any, Set
from onyx.memory.manager import MemoryManager
from onyx.memory.categories import MemoryCategory


@dataclass
class ObsidianNote:
    file_path: str
    title: str
    tags: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    content: str = ""
    modified_time: float = 0.0


class ObsidianSyncEngine:
    """Synchronizes Obsidian vault markdown notes, daily journals, and connections into ONYX memory."""

    def __init__(self, memory: MemoryManager, vault_path: Optional[str] = None):
        self.memory = memory
        self.vault_path = Path(vault_path) if vault_path else None

    def set_vault_path(self, path: str) -> None:
        self.vault_path = Path(os.path.expanduser(path)).resolve()
        if not self.vault_path.exists():
            self.vault_path.mkdir(parents=True, exist_ok=True)

    def parse_note(self, file_path: Path) -> Optional[ObsidianNote]:
        """Extract markdown content, frontmatter tags, and wikilinks."""
        if not file_path.suffix.lower() == ".md":
            return None

        try:
            raw = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        title = file_path.stem
        # Extract YAML frontmatter tags
        tags: List[str] = re.findall(r"#([\w\-_/]+)", raw)
        
        # Extract Obsidian wikilinks [[Target]] or [[Target|Alias]]
        raw_links = re.findall(r"\[\[(.*?)\]\]", raw)
        clean_links: List[str] = [l.split("|")[0].strip() for l in raw_links if l.strip()]

        # Strip frontmatter for clean content
        content = re.sub(r"^---\n.*?\n---\n", "", raw, flags=re.DOTALL).strip()

        return ObsidianNote(
            file_path=str(file_path),
            title=title,
            tags=list(set(tags)),
            links=list(set(clean_links)),
            content=content,
            modified_time=file_path.stat().st_mtime,
        )

    async def sync_vault(self, custom_vault_path: Optional[str] = None) -> Dict[str, Any]:
        """Scan all markdown notes in vault and index into ONYX personal memory."""
        if custom_vault_path:
            self.set_vault_path(custom_vault_path)

        if not self.vault_path or not self.vault_path.exists():
            # If no vault configured, create a default local Obsidian workspace
            default_p = Path("data/obsidian_vault").resolve()
            default_p.mkdir(parents=True, exist_ok=True)
            self.vault_path = default_p

        notes_indexed = 0
        connections_found = 0
        categories_updated: Set[str] = set()

        for root, dirs, files in os.walk(self.vault_path):
            # Ignore .obsidian and .git system folders
            if ".obsidian" in root or ".git" in root:
                continue

            for file in files:
                if file.endswith(".md"):
                    fpath = Path(root) / file
                    note = self.parse_note(fpath)
                    if not note or len(note.content) < 10:
                        continue

                    # Classify note into appropriate ONYX memory category
                    lower_content = note.content.lower()
                    lower_title = note.title.lower()

                    if any(t in ["#connection", "#crm", "#people", "#contact"] for t in note.tags) or "contact" in lower_title:
                        category = MemoryCategory.PROJECTS
                        prefix = f"[Obsidian Connection: {note.title}]"
                        connections_found += 1
                    elif any(t in ["#business", "#deal", "#company", "#venture"] for t in note.tags) or "deal" in lower_title:
                        category = MemoryCategory.PROJECTS
                        prefix = f"[Obsidian Business Venture: {note.title}]"
                    elif "daily" in lower_title or re.match(r"\d{4}-\d{2}-\d{2}", note.title):
                        category = MemoryCategory.EPISODIC
                        prefix = f"[Obsidian Daily Note: {note.title}]"
                    else:
                        category = MemoryCategory.LONG_TERM_KNOWLEDGE
                        prefix = f"[Obsidian Note: {note.title}]"

                    # Prepare indexed content
                    links_str = f"\nRelated Connections: {', '.join(note.links)}" if note.links else ""
                    tags_str = f"\nTags: {', '.join(note.tags)}" if note.tags else ""
                    indexed_text = f"{prefix}\n{note.content[:2000]}{links_str}{tags_str}"

                    await self.memory.remember(
                        content=indexed_text,
                        category=category,
                        metadata={
                            "source": "obsidian",
                            "file": note.file_path,
                            "title": note.title,
                            "tags": note.tags,
                            "links": note.links,
                            "updated_at": note.modified_time,
                        },
                        source=f"obsidian:{note.title}",
                    )
                    notes_indexed += 1
                    categories_updated.add(category.value)

        return {
            "vault_path": str(self.vault_path),
            "notes_indexed": notes_indexed,
            "connections_found": connections_found,
            "categories": list(categories_updated),
            "synced_at": time.time(),
        }
