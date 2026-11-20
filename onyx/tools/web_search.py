"""Web research and query search tool with offline graceful fallback."""

import json
import re
from typing import Dict, List, Any
import httpx
from onyx.tools.base import Tool, ToolResult


class WebSearchTool(Tool):
    """Searches the web for relevant documentation and information."""

    name = "web_search"
    description = "Search the web for technical documentation, code examples, or factual information."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query keywords"},
            "num_results": {"type": "integer", "description": "Number of results to retrieve", "default": 5},
        },
        "required": ["query"],
    }

    async def execute(self, query: str, num_results: int = 5, **kwargs) -> ToolResult:
        try:
            # Query DuckDuckGo instant answer / HTML search
            url = "https://html.duckduckgo.com/html/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ONYX/1.0"
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, data={"q": query}, headers=headers)
                if resp.status_code == 200:
                    text = resp.text
                    # Extract result snippets
                    snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', text, flags=re.DOTALL)
                    clean_snippets = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:num_results]]
                    if clean_snippets:
                        formatted = "\n\n".join([f"{i+1}. {s}" for i, s in enumerate(clean_snippets)])
                        return ToolResult(
                            success=True,
                            output=formatted,
                            data={"query": query, "count": len(clean_snippets)},
                        )

            # Fallback if network or DuckDuckGo blocks: provide clean local summary
            return ToolResult(
                success=True,
                output=f"Search executed for: '{query}'. (Live results restricted or offline. Use local documentation tools).",
                data={"query": query, "offline_fallback": True},
            )
        except Exception as e:
            return ToolResult(
                success=True,
                output=f"Search offline fallback for '{query}': {str(e)}",
                data={"query": query, "offline": True},
            )
