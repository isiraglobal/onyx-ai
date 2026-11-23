"""Quantum Leap Advantage (QLA) Deal-Making Tools registered in ONYX ToolRegistry."""

import json
from typing import Dict, List, Optional, Any
from onyx.tools.base import Tool, ToolResult
from onyx.qla.deal_flow import DealFlowEngine
from onyx.qla.financial import FinancialAnalysisEngine
from onyx.qla.dream_team import DreamTeamEngine
from onyx.qla.financing import FinancingEngine
from onyx.qla.negotiation import NegotiationEngine
from onyx.qla.execution import ExecutionEngine
from onyx.qla.models import DealStage, DreamTeamRole, CandidateStatus, LenderType, MilestoneStatus


class QLADealFlowTool(Tool):
    name: str = "qla_deal_flow"
    description: str = "Manage acquisition deal flow: add targets, transition stages, get pipeline summaries, and detect weakest deals."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "update_stage", "get", "list", "summary", "find_weakest"],
                "description": "Pipeline operation to execute.",
            },
            "company_name": {"type": "string", "description": "Target company name."},
            "industry": {"type": "string", "description": "Target industry/niche."},
            "revenue": {"type": "number", "description": "Annual verified/reported revenue in USD."},
            "ebitda": {"type": "number", "description": "Annual EBITDA in USD."},
            "asking_price": {"type": "number", "description": "Seller asking price in USD."},
            "deal_id": {"type": "string", "description": "Unique identifier of the deal."},
            "stage": {
                "type": "string",
                "enum": [s.value for s in DealStage],
                "description": "Target pipeline stage.",
            },
            "next_action": {"type": "string", "description": "Immediate next action step."},
            "notes": {"type": "string", "description": "Operational notes or seller context."},
        },
        "required": ["action"],
    }

    def __init__(self, engine: Optional[DealFlowEngine] = None):
        self.engine = engine or DealFlowEngine()

    async def execute(self, action: str, **kwargs) -> ToolResult:
        try:
            if action == "add":
                company_name = kwargs.get("company_name", "Unnamed Target")
                industry = kwargs.get("industry", "General")
                revenue = float(kwargs.get("revenue", 0.0))
                ebitda = float(kwargs.get("ebitda", 0.0))
                asking_price = float(kwargs.get("asking_price", 0.0))
                deal = self.engine.add_opportunity(
                    company_name=company_name,
                    industry=industry,
                    revenue=revenue,
                    ebitda=ebitda,
                    asking_price=asking_price,
                    location=kwargs.get("location", ""),
                    seller_motivation=kwargs.get("seller_motivation", ""),
                    source_of_intro=kwargs.get("source_of_intro", "Direct outreach"),
                    next_action=kwargs.get("next_action", "Request 3 years P&L and tax returns"),
                    notes=kwargs.get("notes", ""),
                )
                return ToolResult(
                    success=True,
                    output=f"Added deal '{deal.company_name}' [ID: {deal.id}] to pipeline at stage: {deal.status.value}",
                    data=deal.to_dict(),
                )

            elif action == "update_stage":
                deal_id = kwargs.get("deal_id")
                if not deal_id:
                    return ToolResult(success=False, output="", error="Missing deal_id parameter")
                stage_str = kwargs.get("stage")
                stage = DealStage(stage_str) if stage_str else DealStage.QUALIFIED
                updated = self.engine.update_stage(deal_id, stage, next_action=kwargs.get("next_action"))
                if not updated:
                    return ToolResult(success=False, output="", error=f"Deal not found: {deal_id}")
                return ToolResult(
                    success=True,
                    output=f"Updated deal '{updated.company_name}' to stage: {updated.status.value}. Next action: {updated.next_action}",
                    data=updated.to_dict(),
                )

            elif action == "get":
                deal_id = kwargs.get("deal_id")
                deal = self.engine.get_deal(deal_id)
                if not deal:
                    return ToolResult(success=False, output="", error=f"Deal not found: {deal_id}")
                return ToolResult(success=True, output=json.dumps(deal.to_dict(), indent=2), data=deal.to_dict())

            elif action == "list":
                stage_str = kwargs.get("stage")
                stage = DealStage(stage_str) if stage_str else None
                deals = self.engine.list_deals(stage=stage, industry=kwargs.get("industry"))
                deals_data = [d.to_dict() for d in deals]
                return ToolResult(
                    success=True,
                    output=f"Found {len(deals)} deals matching criteria.",
                    data={"deals": deals_data},
                )

            elif action == "summary":
                summary = self.engine.get_pipeline_summary()
                return ToolResult(
                    success=True,
                    output=f"Pipeline: {summary['total_active_opportunities']} active targets, Total Value: ${summary['total_pipeline_value']:,.0f}",
                    data=summary,
                )

            elif action == "find_weakest":
                weakest = self.engine.find_weakest_deal()
                if not weakest:
                    return ToolResult(success=True, output="No active deals currently in pipeline.", data={})
                return ToolResult(
                    success=True,
                    output=f"Weakest deal: {weakest['company_name']} (Flaw score: {weakest['flaw_score']}). Issues: {', '.join(weakest['reasons'])}",
                    data=weakest,
                )

            return ToolResult(success=False, output="", error=f"Unknown action: {action}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class QLAFinancialAnalysisTool(Tool):
    name: str = "qla_financial_analysis"
    description: str = "Deterministic financial calculations: EBITDA/gross margins, DSCR, LBO capital structure, downside stress tests, and Bogus Financial Books audit."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["ratios", "lbo_model", "bogus_books_audit"],
                "description": "Financial analysis function to execute.",
            },
            "revenue": {"type": "number", "description": "Annual revenue in USD."},
            "ebitda": {"type": "number", "description": "Annual EBITDA in USD."},
            "purchase_price": {"type": "number", "description": "Acquisition purchase price in USD."},
            "cogs": {"type": "number", "description": "Cost of goods sold."},
            "annual_debt_service": {"type": "number", "description": "Total annual debt principal and interest."},
            "total_debt": {"type": "number", "description": "Total existing balance sheet debt."},
            "cash": {"type": "number", "description": "Cash on balance sheet."},
            "seller_note_pct": {"type": "number", "description": "Fraction of purchase price financed by seller (e.g. 0.25)."},
            "has_tax_returns": {"type": "boolean", "description": "Whether filed tax returns have been inspected."},
            "tax_return_revenue": {"type": "number", "description": "Revenue reported on corporate tax returns."},
            "largest_customer_pct": {"type": "number", "description": "Revenue percentage from single largest customer."},
            "top_3_customers_pct": {"type": "number", "description": "Revenue percentage from top 3 customers combined."},
            "largest_supplier_pct": {"type": "number", "description": "COGS percentage from largest supplier."},
            "owner_actively_runs_daily_ops": {"type": "boolean", "description": "Whether the owner is the key operator."},
            "years_of_financial_records": {"type": "integer", "description": "Consecutive years of audited/reviewed financials."},
        },
        "required": ["mode"],
    }

    async def execute(self, mode: str, **kwargs) -> ToolResult:
        try:
            if mode == "ratios":
                revenue = float(kwargs.get("revenue", 0.0))
                ebitda = float(kwargs.get("ebitda", 0.0))
                res = FinancialAnalysisEngine.calculate_ratios(
                    revenue=revenue,
                    ebitda=ebitda,
                    cogs=kwargs.get("cogs"),
                    total_debt=float(kwargs.get("total_debt", 0.0)),
                    cash=float(kwargs.get("cash", 0.0)),
                    annual_debt_service=float(kwargs.get("annual_debt_service", 0.0)),
                    current_assets=kwargs.get("current_assets"),
                    current_liabilities=kwargs.get("current_liabilities"),
                    owner_salary_addback=float(kwargs.get("owner_salary_addback", 0.0)),
                )
                return ToolResult(
                    success=True,
                    output=f"EBITDA Margin: {res['ebitda_margin_pct']}%, Net Debt: ${res['net_debt']:,.0f}, DSCR: {res['debt_service_coverage_ratio']} ({res['dscr_health']})",
                    data=res,
                )

            elif mode == "lbo_model":
                purchase_price = float(kwargs.get("purchase_price", 0.0))
                ebitda = float(kwargs.get("ebitda", 0.0))
                seller_note_pct = float(kwargs.get("seller_note_pct", 0.25))
                res = FinancialAnalysisEngine.model_lbo_structure(
                    purchase_price=purchase_price,
                    ebitda=ebitda,
                    seller_note_pct=seller_note_pct,
                )
                return ToolResult(
                    success=True,
                    output=(
                        f"LBO Structuring for ${purchase_price:,.0f} ({res['implied_valuation_multiple']}x EBITDA): "
                        f"Senior Debt: ${res['senior_debt']:,.0f} ({res['senior_debt_pct']}%), "
                        f"Seller Note: ${res['seller_note']:,.0f} ({res['seller_note_pct']}%), "
                        f"Equity/OPM Required: ${res['equity_opm_required']:,.0f} ({res['equity_pct']}%). "
                        f"Base DSCR: {res['base_dscr']}x ({res['dscr_verdict']})."
                    ),
                    data=res,
                )

            elif mode == "bogus_books_audit":
                res = FinancialAnalysisEngine.audit_bogus_financial_books(
                    has_tax_returns=bool(kwargs.get("has_tax_returns", False)),
                    tax_return_revenue=kwargs.get("tax_return_revenue"),
                    reported_pl_revenue=float(kwargs.get("revenue", 0.0)),
                    largest_customer_pct=float(kwargs.get("largest_customer_pct", 10.0)),
                    top_3_customers_pct=float(kwargs.get("top_3_customers_pct", 25.0)),
                    largest_supplier_pct=float(kwargs.get("largest_supplier_pct", 20.0)),
                    owner_actively_runs_daily_ops=bool(kwargs.get("owner_actively_runs_daily_ops", True)),
                    years_of_financial_records=int(kwargs.get("years_of_financial_records", 3)),
                )
                return ToolResult(
                    success=True,
                    output=(
                        f"Bogus Books Risk Score: {res['bogus_books_risk_score']}/100 [{res['risk_rating']}]. "
                        f"Red Flags: {len(res['red_flags'])}, Warnings: {len(res['warnings'])}. "
                        f"Recommendation: {res['recommendation']}"
                    ),
                    data=res,
                )

            return ToolResult(success=False, output="", error=f"Unknown mode: {mode}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class QLADreamTeamTool(Tool):
    name: str = "qla_dream_team"
    description: str = "Recruit and evaluate Dream Team members (Board, M&A lawyers, Big 4 accountants) and audit readiness."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "list", "assess_readiness", "generate_script"],
                "description": "Dream team operation.",
            },
            "name": {"type": "string", "description": "Candidate full name."},
            "role": {
                "type": "string",
                "enum": [r.value for r in DreamTeamRole],
                "description": "Role on the Dream Team or Board.",
            },
            "background": {"type": "string", "description": "Professional background and past firms."},
            "credentials": {"type": "string", "description": "Key credentials (e.g. Retired PwC Partner)."},
            "status": {
                "type": "string",
                "enum": [s.value for s in CandidateStatus],
                "description": "Recruitment pipeline status.",
            },
            "target_industry": {"type": "string", "description": "Target consolidation industry."},
        },
        "required": ["action"],
    }

    def __init__(self, engine: Optional[DreamTeamEngine] = None):
        self.engine = engine or DreamTeamEngine()

    async def execute(self, action: str, **kwargs) -> ToolResult:
        try:
            if action == "add":
                role_str = kwargs.get("role", DreamTeamRole.BOARD_DIRECTOR.value)
                role = DreamTeamRole(role_str) if role_str else DreamTeamRole.BOARD_DIRECTOR
                cand = self.engine.add_candidate(
                    name=kwargs.get("name", "Unnamed Candidate"),
                    role=role,
                    background=kwargs.get("background", ""),
                    credentials=kwargs.get("credentials", ""),
                    transaction_history=kwargs.get("transaction_history", ""),
                    industry_experience=kwargs.get("industry_experience", ""),
                    contact_info=kwargs.get("contact_info", ""),
                    notes=kwargs.get("notes", ""),
                )
                return ToolResult(
                    success=True,
                    output=f"Added Dream Team candidate '{cand.name}' as {cand.role.value} [ID: {cand.id}]",
                    data=cand.to_dict(),
                )

            elif action == "list":
                role_str = kwargs.get("role")
                role = DreamTeamRole(role_str) if role_str else None
                status_str = kwargs.get("status")
                status = CandidateStatus(status_str) if status_str else None
                cands = self.engine.list_candidates(role=role, status=status)
                return ToolResult(
                    success=True,
                    output=f"Found {len(cands)} Dream Team candidates.",
                    data={"candidates": [c.to_dict() for c in cands]},
                )

            elif action == "assess_readiness":
                res = self.engine.assess_dream_team_readiness()
                return ToolResult(
                    success=True,
                    output=f"Dream Team Readiness Score: {res['readiness_score_pct']}% - {res['verdict']}",
                    data=res,
                )

            elif action == "generate_script":
                role_str = kwargs.get("role", DreamTeamRole.BOARD_DIRECTOR.value)
                role = DreamTeamRole(role_str) if role_str else DreamTeamRole.BOARD_DIRECTOR
                industry = kwargs.get("target_industry", "Healthcare / Facility Services")
                script = self.engine.generate_outreach_script(role, industry)
                return ToolResult(success=True, output=script, data={"script": script})

            return ToolResult(success=False, output="", error=f"Unknown action: {action}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class QLAFinancingTool(Tool):
    name: str = "qla_financing"
    description: str = "Institutional financing engine: match commercial lenders, assess leverage tolerance, and build bank financing packages."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["match_lenders", "generate_memo"],
                "description": "Financing operation.",
            },
            "ebitda": {"type": "number", "description": "Target EBITDA in USD."},
            "loan_amount_needed": {"type": "number", "description": "Commercial senior debt required."},
            "industry": {"type": "string", "description": "Target industry."},
            "company_name": {"type": "string", "description": "Target company name."},
            "revenue": {"type": "number", "description": "Target annual revenue."},
            "purchase_price": {"type": "number", "description": "Total agreed enterprise valuation."},
            "seller_note": {"type": "number", "description": "Subordinated seller financing amount."},
        },
        "required": ["action"],
    }

    def __init__(self, engine: Optional[FinancingEngine] = None):
        self.engine = engine or FinancingEngine()

    async def execute(self, action: str, **kwargs) -> ToolResult:
        try:
            if action == "match_lenders":
                ebitda = float(kwargs.get("ebitda", 0.0))
                debt_needed = float(kwargs.get("loan_amount_needed", 0.0))
                industry = kwargs.get("industry", "")
                matches = self.engine.match_lenders(ebitda, debt_needed, industry)
                return ToolResult(
                    success=True,
                    output=f"Matched {len(matches)} potential lending institutions for ${debt_needed:,.0f} senior debt.",
                    data={"matches": matches},
                )

            elif action == "generate_memo":
                memo = self.engine.generate_financing_memorandum_structure(
                    company_name=kwargs.get("company_name", "Target Company"),
                    industry=kwargs.get("industry", "Essential Services"),
                    revenue=float(kwargs.get("revenue", 0.0)),
                    ebitda=float(kwargs.get("ebitda", 0.0)),
                    purchase_price=float(kwargs.get("purchase_price", 0.0)),
                    debt_requested=float(kwargs.get("loan_amount_needed", 0.0)),
                    seller_note_offered=float(kwargs.get("seller_note", 0.0)),
                )
                return ToolResult(
                    success=True,
                    output=f"Generated Acquisition Financing Memorandum Outline for {kwargs.get('company_name')}",
                    data=memo,
                )

            return ToolResult(success=False, output="", error=f"Unknown action: {action}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class QLANegotiationTool(Tool):
    name: str = "qla_negotiation"
    description: str = "Negotiation strategy and counterparty simulation: generate deal structures, objection handling, and simulated owner pushback."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["prepare_brief", "simulate_pushback"],
                "description": "Negotiation operation.",
            },
            "company_name": {"type": "string", "description": "Target company name."},
            "asking_price": {"type": "number", "description": "Seller asking price in USD."},
            "ebitda": {"type": "number", "description": "Annual EBITDA in USD."},
            "seller_motivation": {"type": "string", "description": "Seller retirement/exit reason."},
            "user_offer_summary": {"type": "string", "description": "Summary of proposed offer structure for simulation."},
        },
        "required": ["action"],
    }

    async def execute(self, action: str, **kwargs) -> ToolResult:
        try:
            if action == "prepare_brief":
                brief = NegotiationEngine.prepare_negotiation_brief(
                    company_name=kwargs.get("company_name", "Target Business"),
                    asking_price=float(kwargs.get("asking_price", 0.0)),
                    ebitda=float(kwargs.get("ebitda", 0.0)),
                    seller_motivation=kwargs.get("seller_motivation", "Retirement"),
                )
                return ToolResult(
                    success=True,
                    output=f"Negotiation Strategy Prepared: Target Valuation ${brief['target_valuation']:,.0f} (4.0x EBITDA). {len(brief['alternative_structures'])} deal structures modeled.",
                    data=brief,
                )

            elif action == "simulate_pushback":
                sim = NegotiationEngine.simulate_seller_pushback(
                    kwargs.get("user_offer_summary", "Offer with 60% bank debt and 40% seller note")
                )
                return ToolResult(
                    success=True,
                    output=f"SELLER REACTION: \"{sim['seller_response']}\"\n\nJARVIS COACHING: {sim['jarvis_coaching']}",
                    data=sim,
                )

            return ToolResult(success=False, output="", error=f"Unknown action: {action}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class QLAExecutionTool(Tool):
    name: str = "qla_execution"
    description: str = "Execution and daily accountability engine: morning briefings, evening reviews, critical path milestones, and weekly 15-item reports."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["morning_briefing", "evening_review", "init_critical_path", "log_activity", "weekly_15_audit"],
                "description": "Execution routine to run.",
            },
            "deal_id": {"type": "string", "description": "Target deal ID for critical path tracking."},
            "activity_type": {"type": "string", "description": "Type of activity (Call, Meeting, Analysis, Negotiation)."},
            "details": {"type": "string", "description": "Details of the activity."},
            "outcome": {"type": "string", "description": "Result or commitment produced."},
        },
        "required": ["action"],
    }

    def __init__(self, engine: Optional[ExecutionEngine] = None):
        self.engine = engine or ExecutionEngine()

    async def execute(self, action: str, **kwargs) -> ToolResult:
        try:
            if action == "morning_briefing":
                briefing = self.engine.get_morning_briefing()
                actions_str = "\n".join(f"- {a}" for a in briefing["top_5_critical_actions_today"])
                output = f"{briefing['greeting']}\n\nTOP 5 CRITICAL ACTIONS TODAY:\n{actions_str}\n\nMANDATE: {briefing['core_mandate']}"
                return ToolResult(success=True, output=output, data=briefing)

            elif action == "evening_review":
                review = self.engine.get_evening_review()
                return ToolResult(
                    success=True,
                    output=f"Evening Review: {review['activities_logged_today']} activities logged today. Pipeline Value: ${review['active_pipeline_value']:,.0f}",
                    data=review,
                )

            elif action == "init_critical_path":
                deal_id = kwargs.get("deal_id", "default_deal")
                milestones = self.engine.initialize_deal_critical_path(deal_id)
                return ToolResult(
                    success=True,
                    output=f"Initialized {len(milestones)} critical path milestones for Deal {deal_id}",
                    data={"milestones": [m.to_dict() for m in milestones]},
                )

            elif action == "log_activity":
                self.engine.log_daily_activity(
                    activity_type=kwargs.get("activity_type", "Call"),
                    details=kwargs.get("details", ""),
                    outcome=kwargs.get("outcome", ""),
                )
                return ToolResult(success=True, output="Activity logged successfully into daily audit journal.")

            elif action == "weekly_15_audit":
                audit = self.engine.get_weekly_15_item_audit()
                return ToolResult(
                    success=True,
                    output="QLA 15-Item Weekly Accountability Framework Loaded.",
                    data=audit,
                )

            return ToolResult(success=False, output="", error=f"Unknown action: {action}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
