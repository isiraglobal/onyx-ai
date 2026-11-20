"""Document ingestion pipeline, chunking, and knowledge extraction."""

import hashlib
from pathlib import Path
import re
import time
from typing import Dict, List, Optional, Any, Tuple
from onyx.memory.manager import MemoryManager
from onyx.memory.categories import MemoryCategory
from onyx.tools.document import DocumentExtractTool


class IngestionPipeline:
    """Ingests multi-format documents, cleans text, and indexes knowledge."""

    def __init__(self, memory: MemoryManager, chunk_size: int = 1000, chunk_overlap: int = 150):
        self.memory = memory
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.doc_tool = DocumentExtractTool()

    def chunk_text(self, text: str) -> List[str]:
        """Split text into semantic chunks with overlap."""
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for para in paragraphs:
            para_len = len(para)
            if current_len + para_len > self.chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                # Retain last paragraph if within overlap limit
                current_chunk = [current_chunk[-1]] if len(current_chunk[-1]) <= self.chunk_overlap else []
                current_len = sum(len(p) for p in current_chunk)

            current_chunk.append(para)
            current_len += para_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks or [text]

    async def ingest_file(
        self,
        file_path: str,
        category: MemoryCategory = MemoryCategory.LONG_TERM_KNOWLEDGE,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract text from file, chunk, and index into structured memory."""
        p = Path(file_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Extract content using DocumentExtractTool
        extract_res = await self.doc_tool.execute(path=str(p))
        if not extract_res.success:
            raise RuntimeError(f"Failed to extract document: {extract_res.error}")

        raw_text = extract_res.output
        chunks = self.chunk_text(raw_text)

        # Compute SHA-256 fingerprint
        file_hash = hashlib.sha256(p.read_bytes()).hexdigest()
        records_created = []

        base_meta = {
            "source_file": p.name,
            "source_path": str(p),
            "file_hash": file_hash,
            "ingested_at": time.time(),
        }
        if custom_metadata:
            base_meta.update(custom_metadata)

        for i, chunk in enumerate(chunks):
            meta = dict(base_meta)
            meta["chunk_index"] = i
            meta["total_chunks"] = len(chunks)

            rec = await self.memory.remember(
                content=chunk,
                category=category,
                metadata=meta,
                source=f"doc:{p.name}",
            )
            records_created.append(rec.id)

        return {
            "file_name": p.name,
            "file_hash": file_hash,
            "chunks_count": len(chunks),
            "record_ids": records_created,
            "category": category.value,
        }
