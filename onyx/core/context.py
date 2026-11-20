"""Multi-turn conversation context manager with token budget allocation."""

from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional, Any


@dataclass
class ConversationTurn:
    role: str  # user, assistant, system, tool
    content: str
    timestamp: float = field(default_factory=time.time)
    tokens_estimate: int = 0

    def __post_init__(self):
        if not self.tokens_estimate:
            self.tokens_estimate = max(1, len(self.content) // 4)


class ContextManager:
    """Manages conversational history, sliding window pruning, and context injection."""

    def __init__(self, max_context_tokens: int = 4096, reserve_completion_tokens: int = 1024):
        self.max_context_tokens = max_context_tokens
        self.reserve_completion_tokens = reserve_completion_tokens
        self.history: List[ConversationTurn] = []

    def add_turn(self, role: str, content: str) -> ConversationTurn:
        turn = ConversationTurn(role=role, content=content)
        self.history.append(turn)
        return turn

    def get_pruned_dialogue(self, system_prompt: str, memory_block: str = "") -> str:
        """Compose context window respecting token limits via sliding window."""
        sys_tokens = (len(system_prompt) + len(memory_block)) // 4
        available_budget = max(10, self.max_context_tokens - self.reserve_completion_tokens - sys_tokens)

        # Select recent turns from newest to oldest
        selected_turns: List[ConversationTurn] = []
        accumulated_tokens = 0

        for turn in reversed(self.history):
            if accumulated_tokens + turn.tokens_estimate > available_budget:
                break
            selected_turns.insert(0, turn)
            accumulated_tokens += turn.tokens_estimate

        # Format full dialogue string
        dialogue_parts = []
        if system_prompt:
            dialogue_parts.append(f"SYSTEM: {system_prompt}")
        if memory_block:
            dialogue_parts.append(f"CONTEXT & MEMORY:\n{memory_block}")

        for t in selected_turns:
            dialogue_parts.append(f"{t.role.upper()}: {t.content}")

        return "\n\n".join(dialogue_parts)

    def clear(self) -> None:
        self.history.clear()
