"""Document parsing and text extraction tool."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from onyx.tools.base import Tool, ToolResult


class DocumentExtractTool(Tool):
    """Extracts clean text and structural content from PDFs, source code, and text files."""

    name = "document_extract"
    description = "Extract and parse textual content from PDF files, source code, JSON, or text documents."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative path to the document file"},
            "max_pages": {"type": "integer", "description": "Max pages to extract if PDF", "default": 20},
        },
        "required": ["path"],
    }

    async def execute(self, path: str, max_pages: int = 20, **kwargs) -> ToolResult:
        file_path = Path(path).resolve()
        if not file_path.exists():
            return ToolResult(success=False, output="", error=f"File not found: {path}")

        suffix = file_path.suffix.lower()

        try:
            if suffix == ".pdf":
                # PDF extraction via pypdf
                from pypdf import PdfReader
                reader = PdfReader(str(file_path))
                total_pages = len(reader.pages)
                pages_to_read = min(total_pages, max_pages)
                extracted_pages = []

                for i in range(pages_to_read):
                    text = reader.pages[i].extract_text() or ""
                    extracted_pages.append(f"--- Page {i + 1} ---\n{text.strip()}")

                full_text = "\n\n".join(extracted_pages)
                return ToolResult(
                    success=True,
                    output=full_text,
                    data={
                        "format": "pdf",
                        "total_pages": total_pages,
                        "pages_extracted": pages_to_read,
                    },
                )

            elif suffix in [".json", ".jsonl"]:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                return ToolResult(
                    success=True,
                    output=content[:10000],
                    data={"format": "json", "size_bytes": len(content)},
                )

            else:
                # Text / code file (.txt, .md, .py, .yaml, .c, .rs, etc.)
                content = file_path.read_text(encoding="utf-8", errors="replace")
                return ToolResult(
                    success=True,
                    output=content,
                    data={"format": suffix or "text", "size_bytes": len(content)},
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Document extraction error: {str(e)}")
