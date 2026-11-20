"""Research, Architect, and Developer specialist agents."""

from typing import List
from onyx.agents.base import BaseAgent, AgentTask, TaskStatus, AgentMessage


class ResearchAgent(BaseAgent):
    """Specialist agent for information extraction, web research, and document synthesis."""

    name = "research"
    role_description = "Investigates information, extracts factual data, reads web docs, and synthesizes technical findings."
    system_prompt = (
        "You are the ONYX Research Agent. Your responsibility is thorough, factual information gathering. "
        "Use web search and document extraction tools. Never invent facts, cite sources accurately, and structure findings logically."
    )
    allowed_tools: List[str] = ["web_search", "web_page_read", "document_extract", "file_read"]

    async def execute_task(self, task: AgentTask) -> AgentTask:
        """Execute research task by autonomously running web search and fetching content."""
        task.status = TaskStatus.RUNNING
        clean_query = task.goal.lower()
        for prefix in ["search online for", "search web for", "look up", "research", "find news on", "search for"]:
            clean_query = clean_query.replace(prefix, "")
        clean_query = clean_query.strip(" ?.")

        # Execute web search
        search_res = await self.tools.execute("web_search", {"query": clean_query, "num_results": 4})
        if search_res.success and search_res.output:
            context = f"ONLINE SEARCH FINDINGS FOR '{clean_query}':\n{search_res.output}"
            task.messages.append(AgentMessage(role="user", content=task.goal))
            task.messages.append(AgentMessage(role="tool", content=context, name="web_search"))

            prompt = (
                f"User requested research: '{task.goal}'.\n\n"
                f"Web Search Results:\n{search_res.output}\n\n"
                "Synthesize a concise, direct, high-conviction briefing summarizing the key facts found above. No fluff."
            )
            resp = await self.model.generate(
                prompt=prompt,
                system_prompt=self.format_system_prompt(task),
                temperature=0.2,
                max_tokens=400,
            )
            task.result = resp.content.strip()
            task.messages.append(AgentMessage(role="assistant", content=task.result))
            task.status = TaskStatus.COMPLETED
            return task

        # Fallback to base execution if search had no output
        return await super().execute_task(task)


class ArchitectAgent(BaseAgent):
    """Specialist agent for system design, interface boundaries, and technical trade-offs."""

    name = "architect"
    role_description = "Designs system architecture, modular component interfaces, data schemas, and evaluates engineering trade-offs."
    system_prompt = (
        "You are the ONYX Architect Agent. You design modular, maintainable, and high-performance system architectures. "
        "Avoid unnecessary dependencies and complex abstractions. Prioritize deterministic local execution and clean interfaces."
    )
    allowed_tools: List[str] = ["file_read", "file_list"]


class DeveloperAgent(BaseAgent):
    """Specialist agent for software development, debugging, testing, and file implementation."""

    name = "developer"
    role_description = "Writes, edits, refactors, and debugs code. Executes sandboxed terminal commands and tests."
    system_prompt = (
        "You are the ONYX Developer Agent. You write clean, robust, production-grade Python and systems code. "
        "You write unit tests for your code, run terminal diagnostics inside the sandbox, and verify before declaring completion."
    )
    allowed_tools: List[str] = [
        "file_read", "file_write", "file_list",
        "terminal_run", "python_execute", "git_operations"
    ]
