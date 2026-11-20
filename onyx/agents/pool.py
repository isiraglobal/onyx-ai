"""Agent pool and dynamic specialist agent factory."""

from typing import Dict, List, Optional, Any
from onyx.agents.base import BaseAgent
from onyx.agents.specialists import ResearchAgent, ArchitectAgent, DeveloperAgent
from onyx.agents.data_and_ops import DataAgent, ModelAgent, MemoryAgent, EvaluationAgent, SecurityAgent
from onyx.agents.quantum_leap import QuantumLeapAgent
from onyx.agents.supervisor import SupervisorAgent
from onyx.models.base import ModelAdapter
from onyx.tools.registry import ToolRegistry
from onyx.memory.manager import MemoryManager


class DynamicSpecialistAgent(BaseAgent):
    """Temporary agent created dynamically for a specialized domain or workflow."""

    def __init__(
        self,
        name: str,
        role_description: str,
        system_prompt: str,
        allowed_tools: List[str],
        model: ModelAdapter,
        tools: Optional[ToolRegistry] = None,
        memory: Optional[MemoryManager] = None,
    ):
        super().__init__(model=model, tools=tools, memory=memory)
        self.name = name
        self.role_description = role_description
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools


class AgentPool:
    """Manages life cycle of standard specialist agents and dynamic temporary agents."""

    def __init__(
        self,
        model: ModelAdapter,
        tools: Optional[ToolRegistry] = None,
        memory: Optional[MemoryManager] = None,
    ):
        self.model = model
        self.tools = tools or ToolRegistry()
        self.memory = memory
        self.agents: Dict[str, BaseAgent] = {}
        self._initialize_standard_agents()

    def _initialize_standard_agents(self) -> None:
        """Create standard core specialist agents."""
        self.agents["research"] = ResearchAgent(self.model, self.tools, self.memory)
        self.agents["architect"] = ArchitectAgent(self.model, self.tools, self.memory)
        self.agents["developer"] = DeveloperAgent(self.model, self.tools, self.memory)
        self.agents["data"] = DataAgent(self.model, self.tools, self.memory)
        self.agents["model"] = ModelAgent(self.model, self.tools, self.memory)
        self.agents["memory"] = MemoryAgent(self.model, self.tools, self.memory)
        self.agents["evaluation"] = EvaluationAgent(self.model, self.tools, self.memory)
        self.agents["security"] = SecurityAgent(self.model, self.tools, self.memory)
        self.agents["quantum_leap"] = QuantumLeapAgent(self.model, self.tools, self.memory)

        # Supervisor coordinates all of them
        supervisor = SupervisorAgent(self.model, self.agents, self.tools, self.memory)
        self.agents["supervisor"] = supervisor

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        return self.agents.get(name)

    def spawn_temporary_agent(
        self,
        name: str,
        role_description: str,
        instructions: str,
        allowed_tools: Optional[List[str]] = None,
    ) -> BaseAgent:
        """Dynamically instantiate a temporary specialist agent."""
        temp_agent = DynamicSpecialistAgent(
            name=name,
            role_description=role_description,
            system_prompt=instructions,
            allowed_tools=allowed_tools or [],
            model=self.model,
            tools=self.tools,
            memory=self.memory,
        )
        self.agents[name] = temp_agent
        # Also register with supervisor
        if "supervisor" in self.agents and isinstance(self.agents["supervisor"], SupervisorAgent):
            self.agents["supervisor"].register_specialist(temp_agent)
        return temp_agent

    def list_agents(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": a.name,
                "role": a.role_description,
                "allowed_tools": a.allowed_tools,
            }
            for a in self.agents.values()
        ]
