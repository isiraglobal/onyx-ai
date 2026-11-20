"""Task routing and agent classification engine."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class RouteDecision:
    task_category: str
    target_agent: str
    target_model_tier: str  # fast | standard | heavy
    needs_tools: bool
    rationale: str


class TaskRouter:
    """Classifies user inquiries and routes to optimal agents and model tiers."""

    def route_task(self, prompt: str) -> RouteDecision:
        p_lower = prompt.lower()

        # 0. Quantum Leap Advantage (QLA) Acquisitions & Deal Structuring
        if any(w in p_lower for w in ["qla", "quantum leap", "bodacious goal", "seller finance", "leveraged buyout", "lbo", "dream team", "roll-up", "rollup", "acquisition vehicle", "fragmented industry", "trillion dollar man"]):
            return RouteDecision(
                task_category="qla_acquisitions",
                target_agent="quantum_leap",
                target_model_tier="standard",
                needs_tools=False,
                rationale="Direct Quantum Leap Advantage (QLA) guidance via QuantumLeapAgent.",
            )

        # 1. Research queries & Real-world Knowledge Lookup
        # Triggers for news, external entity lookups, search requests, or current events
        research_triggers = [
            "research", "investigate", "look up", "documentation for", "articles on", "search",
            "search web", "search online", "latest news", "recent news", "news about", "what is",
            "who is", "tell me about", "browse", "find out", "google"
        ]
        if any(w in p_lower for w in research_triggers):
            # If asking about known local memory/books/network, keep direct unless explicitly asking to search or for unknown entities
            if not any(w in p_lower for w in ["search", "latest", "news", "google", "online", "current"]):
                if any(w in p_lower for w in ["qla", "step", "closing", "htc", "marcus", "elena", "david", "author", "book"]):
                    return RouteDecision(
                        task_category="general",
                        target_agent="supervisor",
                        target_model_tier="fast",
                        needs_tools=False,
                        rationale="Local personal memory or book doctrine inquiry.",
                    )

            return RouteDecision(
                task_category="research",
                target_agent="research",
                target_model_tier="standard",
                needs_tools=True,
                rationale="Requires web research or document extraction.",
            )

        # 2. Software development & debugging
        if any(w in p_lower for w in ["write code", "implement", "fix bug", "refactor", "create script", "function", "class", "debug"]):
            return RouteDecision(
                task_category="development",
                target_agent="developer",
                target_model_tier="heavy",
                needs_tools=True,
                rationale="Requires software coding, sandbox execution, and testing.",
            )

        # 3. System architecture
        if any(w in p_lower for w in ["architect", "system design", "schema design", "tradeoffs", "components"]):
            return RouteDecision(
                task_category="architecture",
                target_agent="architect",
                target_model_tier="standard",
                needs_tools=False,
                rationale="Requires architectural design and modular planning.",
            )

        # 4. Security auditing
        if any(w in p_lower for w in ["security", "vulnerability", "permission", "exploit", "audit"]):
            return RouteDecision(
                task_category="security",
                target_agent="security",
                target_model_tier="standard",
                needs_tools=True,
                rationale="Requires security inspection and permission verification.",
            )

        # 5. Default: Direct supervisor handling
        return RouteDecision(
            task_category="general",
            target_agent="supervisor",
            target_model_tier="fast",
            needs_tools=False,
            rationale="Standard conversational or general inquiry handled directly.",
        )
