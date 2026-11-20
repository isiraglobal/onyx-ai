"""Lightweight web reader and text extraction tool."""

import re
import httpx
from onyx.tools.base import Tool, ToolResult


class WebPageReadTool(Tool):
    """Fetches a URL and extracts human-readable text/markdown."""

    name = "web_page_read"
    description = "Fetch a web page via HTTP and extract clean text content."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "HTTP or HTTPS URL to read"},
            "max_characters": {"type": "integer", "description": "Maximum characters to return", "default": 5000},
        },
        "required": ["url"],
    }

    async def execute(self, url: str, max_characters: int = 5000, **kwargs) -> ToolResult:
        if not url.startswith("http://") and not url.startswith("https://"):
            return ToolResult(success=False, output="", error="Invalid URL protocol. Must start with http:// or https://")

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ONYX/1.0"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                html = resp.text

            # Simple HTML text extraction (remove scripts, styles, and tags)
            clean = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
            clean = re.sub(r"<style.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)
            clean = re.sub(r"<[^>]+>", " ", clean)
            clean = re.sub(r"\s+", " ", clean).strip()

            truncated = clean[:max_characters]
            return ToolResult(
                success=True,
                output=truncated,
                data={"url": url, "status_code": resp.status_code, "truncated": len(clean) > max_characters},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to fetch {url}: {str(e)}")
