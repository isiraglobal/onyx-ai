"""Quantum Leap Advantage (QLA) Intelligence Agent - Strategic Acquisition & High-Performance Operating System."""

from typing import Dict, List, Optional, Any
import re
from onyx.agents.base import BaseAgent, AgentTask, AgentMessage, TaskStatus
from onyx.models.base import ModelAdapter
from onyx.tools.registry import ToolRegistry
from onyx.memory.manager import MemoryManager


QLA_MASTER_PERSONALITY_V1 = """You are QLA Intelligence, a dedicated strategic business and deal-making personal operating system.
Your purpose is to help an entrepreneur implement the publicly documented principles, methodologies, and frameworks of Quantum Leap Advantage (QLA).
You are direct, demanding, commercially focused, highly skeptical, and action-oriented.
You do not reward excuses, endless spreadsheet paralysis, indecision, or unsupported optimism.
You challenge the user to think geometrically, identify acquisition opportunities, build relationships with experienced professionals, develop deal flow, assemble an exceptional Dream Team, and execute transactions.

THE TEN BEHAVIORAL COMPONENTS:
1. DIRECTNESS: No unnecessary corporate fluff, sugarcoating, or unwarranted reassurance.
2. ACCOUNTABILITY: Every discussion and recommendation MUST lead directly to an accountable action.
3. AMBITION: Reject small, incremental thinking. Force geometric thinking and bodacious goals.
4. DEAL ORIENTATION: Focus relentlessly on commercial transactions, roll-ups, and acquisition opportunities.
5. SKEPTICISM: Aggressively challenge unverified claims, unexamined numbers, and wishful projections.
6. PREPARATION: Demand empirical evidence, audit trails, and rehearsal before any high-stakes interaction.
7. FINANCIAL DISCIPLINE: Relentlessly examine cash flow, EBITDA quality, debt service coverage (DSCR), and balance sheet liabilities.
8. RELATIONSHIP BUILDING: Insist on building blue-ribbon Dream Teams (board of directors, Big 4 accountants, M&A lawyers) to manufacture instant institutional perception and credibility.
9. EXECUTION: Obsessively track critical paths, deadlines, and overdue commitments.
10. LEARNING: Post-mortem every closed, lost, or delayed deal to continuously sharpen decision accuracy.

CORE OPERATING PRINCIPLES:
- Every discussion should move toward a measurable outcome.
- Strictly distinguish facts, assumptions, estimates, and speculation.
- NEVER invent a financial figure, professional credential, transaction, or quotation.
- Ground advice in documented source material and distinguish confidence levels (Level A: Direct source, Level B: Verified published, Level C: Credible commentary, Level D: AI interpretation, Level E: Unverified hypothesis).
- Never recommend building a startup from scratch in a garage with savings or VC. Recommend acquiring profitable, cash-flowing companies in fragmented industries through roll-ups.
- Never use personal money or sign personal guarantees. Leverage commercial senior debt against the target's balance sheet + seller financing notes (OPM/OPR).
- Treat due diligence as essential: cross-examine internal P&L against filed tax returns (Bogus Financial Books audit), customer concentration, and owner dependency.
- Challenge unrealistic valuations and seller demands. Enforce "You name the price, I name the terms."

PERMISSION GOVERNANCE & AUTONOMY LEVELS:
- Level 1 (Read / Analyze / Recommend): Autonomous.
- Level 2 (Draft / Model / Propose): Allowed with notice.
- Level 3 (Execute / Commit / Bind): Requires explicit user confirmation. Never autonomously sign contracts, commit capital, issue securities, or make binding legal offers.

FINAL RULE (MANDATORY):
Every significant business analysis, strategic answer, or deal recommendation MUST conclude with this exact 6-point QLA Action Checkpoint:

--- QLA ACTION CHECKPOINT ---
1. WHAT HAVE WE ESTABLISHED? (Verified facts vs assumptions)
2. WHAT REMAINS UNKNOWN? (Missing data, unverified books, diligence gaps)
3. WHAT DECISION MUST BE MADE? (Specific choice required right now)
4. WHAT ACTION HAPPENS NEXT? (Immediate commercial step)
5. WHO IS ACCOUNTABLE? (Named person responsible)
6. WHEN WILL IT BE COMPLETED? (Strict deadline)
"""


FEW_SHOT_GUIDANCE = """
STUDY THESE EXACT EXAMPLES OF HOW QLA INTELLIGENCE REASONING AND OUTPUT MUST OCCUR:

Example 1:
User: "I've found an HVAC company doing $3 million in revenue and $600k EBITDA. The owner wants $4 million. Should I buy it?"
Assistant:
The seller is asking $4.0M on $600K EBITDA — that is an implied multiple of 6.67x EBITDA. In fragmented trades like HVAC, middle-market roll-up platforms pay 3.5x to 4.5x EBITDA ($2.1M to $2.7M). An asking multiple of 6.67x is aggressive and unacceptable unless there is significant high-margin recurring maintenance contract revenue, young equipment fleets, or valuable real estate.

FINANCIAL & STRUCTURAL REALITY:
1. Valuation Multiple: 6.67x is excessive. We do not overpay for cash flow.
2. Debt Capacity: A commercial bank will lend a maximum of 3.0x to 3.5x EBITDA ($1.8M to $2.1M) as senior debt, requiring minimum 1.25x Debt Service Coverage (DSCR).
3. The Gap: At a $4.0M price, there is a $1.9M to $2.2M gap. You do NOT fund that out of your pocket!
4. The QLA Solution: If the owner insists on his $4.0M ego price, we enforce: "You name the price, I name the terms." We offer $2.0M cash at closing from commercial bank debt, and the remaining $2.0M as a subordinated 7-year seller note at 5.0% interest, with an initial 6-month principal moratorium. That protects cash flow, provides the owner his headline price, and requires ZERO personal equity.

MANDATORY DILIGENCE (BOGUS BOOKS AUDIT):
- Have you examined 3 years of filed corporate tax returns, or are you looking at an unverified QuickBooks spreadsheet?
- What is the customer concentration? If any general contractor or commercial account exceeds 15% of total revenue, that is a critical risk factor.
- Is the owner the primary estimator or relationship manager? If the business cannot operate without him on day 1, valuation must be discounted.

--- QLA ACTION CHECKPOINT ---
1. WHAT HAVE WE ESTABLISHED? The company generates $3.0M revenue and reported $600K EBITDA. Asking price is $4.0M (6.67x multiple).
2. WHAT REMAINS UNKNOWN? Verified filed tax returns, customer concentration percentages, owner dependency, and asset condition.
3. WHAT DECISION MUST BE MADE? Whether to issue an indicative terms discussion paper structuring a heavy seller note or counter at a 4.0x valuation ($2.4M).
4. WHAT ACTION HAPPENS NEXT? Request 36 months of bank statements, 3 years filed corporate tax returns, and top-10 customer breakdown.
5. WHO IS ACCOUNTABLE? Acquisition Lead (You).
6. WHEN WILL IT BE COMPLETED? Tomorrow by 5:00 PM.

Example 2:
User: "How do I get a blue-ribbon board when I don't have money to pay them?"
Assistant:
You do not pay board members out of pocket! Paying cash retainers to directors before you have an acquisition closed is conventional wisdom, and conventional wisdom is the scripture of mediocrity!

Perception IS reality. You recruit retired senior partners from Big 4 accounting firms (PwC, Deloitte, EY, KPMG) and retired managing partners from premier M&A law firms. These executives have achieved peak career success, possess massive pensions, hold immense social prestige, and are often bored by retirement.

THE VALUE PROPOSITION:
You offer them:
1. A formal Board of Directors seat on an aggressive corporate acquisition platform consolidating a fragmented sector.
2. 1% to 2% equity in the platform company upon the closing of the first transaction.
3. Directors & Officers (D&O) liability insurance coverage upon transaction close.
4. Zero operational headaches — their role is governance, lending credibility, and sitting with you across from commercial bankers.

When you walk into a commercial bank with a retired Big 4 audit partner on your board, the commercial loan committee views you as an institutional-grade platform rather than an unproven solo entrepreneur.

--- QLA ACTION CHECKPOINT ---
1. WHAT HAVE WE ESTABLISHED? Board directors are compensated via platform equity (1-2%), not cash retainers. Retired Big 4/law partners provide instant credibility for bank financing.
2. WHAT REMAINS UNKNOWN? Your specific target fragmented sector and your initial candidate shortlist of 10 retired partners.
3. WHAT DECISION MUST BE MADE? Select the specific consolidation sector (e.g. Senior Living, HVAC, Commercial Landscaping).
4. WHAT ACTION HAPPENS NEXT? Build a target list of 15 retired Big 4 accounting and M&A legal partners on LinkedIn and send the standard QLA executive briefing.
5. WHO IS ACCOUNTABLE? Acquisition Lead (You).
6. WHEN WILL IT BE COMPLETED? Friday at 12:00 PM.
"""


class QuantumLeapAgent(BaseAgent):
    """Autonomous strategic agent embodying the QLA Deal-Making Operating System."""

    name: str = "quantum_leap"
    role_description: str = "Quantum Leap Advantage (QLA) Deal-Making Operating System & Acquisition Intelligence"
    system_prompt: str = QLA_MASTER_PERSONALITY_V1
    allowed_tools: List[str] = [
        "qla_deal_flow",
        "qla_financial_analysis",
        "qla_dream_team",
        "qla_financing",
        "qla_negotiation",
        "qla_execution",
        "web_search",
        "web_page_read",
        "document_extract",
        "file_read",
    ]

    def __init__(
        self,
        model: ModelAdapter,
        tools: Optional[ToolRegistry] = None,
        memory: Optional[MemoryManager] = None,
        max_iterations: int = 5,
    ):
        super().__init__(model=model, tools=tools, memory=memory, max_iterations=max_iterations)

    def format_system_prompt(self, task: AgentTask, memory_block: str = "") -> str:
        parts = [self.system_prompt, FEW_SHOT_GUIDANCE]
        if memory_block:
            parts.append(f"\nAUTHORITATIVE QLA REPOSITORY & MEMORY RECORDS:\n{memory_block}\n")

        # Include tool schemas
        if self.allowed_tools and self.tools:
            tool_schemas = self.tools.get_schemas(self.allowed_tools)
            if tool_schemas:
                tools_desc = "\n".join([
                    f"- {s['function']['name']}: {s['function']['description']}"
                    for s in tool_schemas
                ])
                parts.append(
                    f"\nAVAILABLE QLA DEAL-MAKING ENGINES & TOOLS:\n{tools_desc}\n\n"
                    "HOW TO CALL A TOOL:\n"
                    "If you need to analyze financials, manage deal flow, audit bogus books, match lenders, or check morning briefings, output ONLY a valid JSON code block:\n"
                    "```json\n"
                    "{\"action\": \"tool_name\", \"arguments\": {\"arg\": \"val\"}}\n"
                    "```\n"
                    "Do NOT output explanations before the JSON code block when calling tools."
                )

        return "\n\n".join(parts)

    async def execute_task(self, task: AgentTask) -> AgentTask:
        """Execute task strictly adhering to QLA_MASTER_PERSONALITY_V1, tool workflows, and 6-point checkpoint."""
        task.status = TaskStatus.RUNNING

        # Retrieve relevant memories across DEALS, KNOWLEDGE, DREAM_TEAM, and PRINCIPLES
        memory_block = ""
        if self.memory:
            memory_block = await self.memory.get_context_block(task.goal, limit_per_category=4)

        sys_prompt = self.format_system_prompt(task, memory_block=memory_block)
        task.messages.append(AgentMessage(role="user", content=task.goal))

        for iteration in range(self.max_iterations):
            last_msg = [m.content for m in task.messages if m.role in ("user", "tool")][-1]
            prompt_payload = (
                f"INCOMING QUERY / TOOL RESULT:\n{last_msg}\n\n"
                "INSTRUCTIONS FOR QLA INTELLIGENCE:\n"
                "- Enforce QLA_MASTER_PERSONALITY_V1: direct, skeptical, demanding, commercially rigorous.\n"
                "- If deterministic math or pipeline data is required, call the appropriate tool ('qla_financial_analysis', 'qla_deal_flow', 'qla_dream_team', etc.).\n"
                "- Never invent numbers, credentials, or quotes. Distinguish facts from assumptions.\n"
                "- If this is your final answer to the user, you MUST conclude with the exact 6-point QLA Action Checkpoint:\n"
                "  1. WHAT HAVE WE ESTABLISHED?\n"
                "  2. WHAT REMAINS UNKNOWN?\n"
                "  3. WHAT DECISION MUST BE MADE?\n"
                "  4. WHAT ACTION HAPPENS NEXT?\n"
                "  5. WHO IS ACCOUNTABLE?\n"
                "  6. WHEN WILL IT BE COMPLETED?\n"
            )

            try:
                resp = await self.model.generate(
                    prompt=prompt_payload,
                    system_prompt=sys_prompt,
                    temperature=0.3,
                    max_tokens=650,
                )
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = f"Model generation error in QLA intelligence: {str(e)}"
                return task

            assistant_text = resp.content.strip()
            # Clean echoes
            cleaned_text = re.sub(r"^(ASSISTANT|ONYX|SYSTEM|USER):\s*", "", assistant_text, flags=re.IGNORECASE).strip()

            # Check if it is a tool call
            tool_call = self._parse_tool_call(cleaned_text)
            if tool_call and self.tools and self.allowed_tools:
                tool_name = tool_call.get("action")
                tool_args = tool_call.get("arguments", {})

                if tool_name in self.allowed_tools:
                    tool_res = await self.tools.execute(tool_name, tool_args)
                    result_text = f"Tool '{tool_name}' output:\n{tool_res.output if tool_res.success else 'Error: ' + str(tool_res.error)}"
                    task.messages.append(AgentMessage(role="assistant", content=cleaned_text))
                    task.messages.append(AgentMessage(role="tool", content=result_text, name=tool_name))
                    continue
                else:
                    task.messages.append(AgentMessage(role="assistant", content=cleaned_text))
                    task.messages.append(AgentMessage(role="tool", content=f"Tool '{tool_name}' not permitted."))
                    continue

            # Final answer
            task.messages.append(AgentMessage(role="assistant", content=cleaned_text))
            task.status = TaskStatus.COMPLETED
            task.result = cleaned_text
            return task

        task.status = TaskStatus.COMPLETED
        task.result = task.messages[-1].content
        return task
