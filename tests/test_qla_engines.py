"""Unit tests for QLA Deal-Making Intelligence Engines, Tools, and Agent."""

import pytest
import tempfile
import shutil
from pathlib import Path

from onyx.qla.models import (
    DealOpportunity,
    DealStage,
    DreamTeamRole,
    CandidateStatus,
    SourceConfidence,
)
from onyx.qla.deal_flow import DealFlowEngine
from onyx.qla.financial import FinancialAnalysisEngine
from onyx.qla.dream_team import DreamTeamEngine
from onyx.qla.financing import FinancingEngine
from onyx.qla.negotiation import NegotiationEngine
from onyx.qla.execution import ExecutionEngine
from onyx.tools.qla_tools import (
    QLADealFlowTool,
    QLAFinancialAnalysisTool,
    QLADreamTeamTool,
    QLAFinancingTool,
    QLANegotiationTool,
    QLAExecutionTool,
)
from onyx.agents.quantum_leap import QuantumLeapAgent, QLA_MASTER_PERSONALITY_V1
from onyx.models.mock import MockModelAdapter
from onyx.tools.registry import ToolRegistry


@pytest.fixture
def temp_qla_env():
    temp_dir = tempfile.mkdtemp(prefix="onyx_qla_test_")
    deals_file = str(Path(temp_dir) / "deals.json")
    dt_file = str(Path(temp_dir) / "dream_team.json")
    lenders_file = str(Path(temp_dir) / "lenders.json")
    exec_file = str(Path(temp_dir) / "execution.json")

    deal_engine = DealFlowEngine(storage_path=deals_file)
    dt_engine = DreamTeamEngine(storage_path=dt_file)
    financing_engine = FinancingEngine(storage_path=lenders_file)
    exec_engine = ExecutionEngine(storage_path=exec_file, deal_engine=deal_engine)

    yield {
        "deal_engine": deal_engine,
        "dt_engine": dt_engine,
        "financing_engine": financing_engine,
        "exec_engine": exec_engine,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_deal_flow_pipeline(temp_qla_env):
    deal_engine: DealFlowEngine = temp_qla_env["deal_engine"]

    # 1. Add deal
    deal = deal_engine.add_opportunity(
        company_name="Apex HVAC Services",
        industry="Commercial HVAC",
        revenue=4_500_000.0,
        ebitda=900_000.0,
        asking_price=3_600_000.0,
        seller_motivation="Retiring founder (65yo)",
    )
    assert deal.company_name == "Apex HVAC Services"
    assert deal.status == DealStage.IDENTIFIED

    # 2. Advance stage
    updated = deal_engine.update_stage(
        deal.id,
        new_stage=DealStage.FINANCIAL_SCREENING,
        next_action="Audit 3 years tax returns",
    )
    assert updated.status == DealStage.FINANCIAL_SCREENING
    assert updated.next_action == "Audit 3 years tax returns"

    # 3. Pipeline summary
    summary = deal_engine.get_pipeline_summary()
    assert summary["total_active_opportunities"] == 1
    assert summary["total_pipeline_value"] == 3_600_000.0
    assert summary["total_pipeline_ebitda"] == 900_000.0


def test_weakest_deal_detection(temp_qla_env):
    deal_engine: DealFlowEngine = temp_qla_env["deal_engine"]

    # Good deal: 4x EBITDA, verified
    deal_engine.add_opportunity(
        company_name="Clean Solid Corp",
        industry="Healthcare",
        revenue=5_000_000.0,
        ebitda=1_000_000.0,
        asking_price=4_000_000.0,
        confidence_rating=SourceConfidence.LEVEL_A.value,
        next_action="LOI draft",
    )

    # Flawed deal: 9x EBITDA, unverified, zero next action
    flawed = deal_engine.add_opportunity(
        company_name="Overpriced Unverified LLC",
        industry="SaaS",
        revenue=2_000_000.0,
        ebitda=200_000.0,
        asking_price=1_800_000.0,
        confidence_rating=SourceConfidence.LEVEL_E.value,
        next_action="",
    )

    weakest = deal_engine.find_weakest_deal()
    assert weakest is not None
    assert weakest["deal_id"] == flawed.id
    assert weakest["flaw_score"] >= 5


def test_deterministic_financial_ratios():
    ratios = FinancialAnalysisEngine.calculate_ratios(
        revenue=10_000_000.0,
        ebitda=2_000_000.0,
        cogs=6_000_000.0,
        total_debt=1_500_000.0,
        cash=500_000.0,
        annual_debt_service=400_000.0,
        owner_salary_addback=250_000.0,
    )

    assert ratios["ebitda_margin_pct"] == 20.0
    assert ratios["gross_profit"] == 4_000_000.0
    assert ratios["gross_margin_pct"] == 40.0
    assert ratios["net_debt"] == 1_000_000.0
    assert ratios["normalized_earnings"] == 2_250_000.0
    assert ratios["debt_service_coverage_ratio"] == 5.0
    assert "Excellent" in ratios["dscr_health"]


def test_lbo_structure_and_stress_testing():
    lbo = FinancialAnalysisEngine.model_lbo_structure(
        purchase_price=5_000_000.0,
        ebitda=1_250_000.0,
        senior_debt_multiple=3.0,
        seller_note_pct=0.25,
    )

    assert lbo["implied_valuation_multiple"] == 4.0
    assert lbo["senior_debt"] == 3_500_000.0  # Capped at 70% of purchase price
    assert lbo["seller_note"] == 1_250_000.0  # 25% seller note
    assert lbo["total_debt_funded"] == 4_750_000.0
    assert lbo["equity_opm_required"] == 250_000.0
    assert lbo["base_dscr"] >= 1.25
    assert "Financially Viable" in lbo["dscr_verdict"]

    # Check stress tests
    stress = lbo["downside_stress_tests"]
    assert "ebitda_down_10pct" in stress
    assert "ebitda_down_20pct" in stress
    assert "ebitda_down_30pct" in stress


def test_bogus_financial_books_audit():
    # Clean company
    clean_audit = FinancialAnalysisEngine.audit_bogus_financial_books(
        has_tax_returns=True,
        tax_return_revenue=5_000_000.0,
        reported_pl_revenue=5_100_000.0,
        largest_customer_pct=8.0,
        top_3_customers_pct=20.0,
        largest_supplier_pct=15.0,
        owner_actively_runs_daily_ops=False,
        years_of_financial_records=4,
    )
    assert clean_audit["bogus_books_risk_score"] < 30
    assert clean_audit["risk_rating"] == "LOW RISK"

    # Red-flag company (missing tax returns + heavy customer concentration + owner dependency)
    dirty_audit = FinancialAnalysisEngine.audit_bogus_financial_books(
        has_tax_returns=False,
        tax_return_revenue=None,
        reported_pl_revenue=3_000_000.0,
        largest_customer_pct=45.0,
        top_3_customers_pct=75.0,
        largest_supplier_pct=50.0,
        owner_actively_runs_daily_ops=True,
        years_of_financial_records=1,
    )
    assert dirty_audit["bogus_books_risk_score"] >= 60
    assert dirty_audit["risk_rating"] == "CRITICAL RISK"
    assert len(dirty_audit["red_flags"]) >= 2
    assert "REJECT / HALT" in dirty_audit["recommendation"]


def test_dream_team_readiness_and_scripts(temp_qla_env):
    dt_engine: DreamTeamEngine = temp_qla_env["dt_engine"]

    # Initial assessment: incomplete
    audit1 = dt_engine.assess_dream_team_readiness()
    assert audit1["readiness_score_pct"] == 0
    assert len(audit1["missing_mandatory_roles"]) == 5

    # Add committed Chairman
    dt_engine.add_candidate(
        name="Sir Arthur Hastings",
        role=DreamTeamRole.CHAIRMAN,
        background="Former CEO of FTSE 250 Facility Services",
        credentials="35 years M&A roll-up leadership",
    )
    cand = list(dt_engine.candidates.values())[0]
    dt_engine.update_status(cand.id, CandidateStatus.COMMITTED)

    audit2 = dt_engine.assess_dream_team_readiness()
    assert audit2["readiness_score_pct"] == 20
    assert DreamTeamRole.CHAIRMAN.value not in audit2["missing_mandatory_roles"]

    # Generate outreach scripts
    script = dt_engine.generate_outreach_script(DreamTeamRole.MA_LAWYER, "Commercial HVAC")
    assert "100% success-fee basis" in script
    assert "Commercial HVAC" in script


def test_financing_and_negotiation():
    # Financing Memo structure
    fin_engine = FinancingEngine()
    memo = fin_engine.generate_financing_memorandum_structure(
        company_name="Titan Logistics",
        industry="Freight & Distribution",
        revenue=12_000_000.0,
        ebitda=2_400_000.0,
        purchase_price=9_600_000.0,
        debt_requested=6_000_000.0,
        seller_note_offered=2_500_000.0,
    )
    assert "CONFIDENTIAL ACQUISITION FINANCING MEMORANDUM" in memo["title"]
    assert len(memo["sections"]) == 5
    assert len(memo["banker_stress_questions_rehearsal"]) == 3

    # Negotiation Brief
    brief = NegotiationEngine.prepare_negotiation_brief(
        company_name="Titan Logistics",
        asking_price=10_000_000.0,
        ebitda=2_000_000.0,
        seller_motivation="Retirement",
    )
    assert brief["headline_asking_price"] == 10_000_000.0
    assert len(brief["alternative_structures"]) >= 3
    assert "I have another buyer offering all cash" in brief["objection_playbook"]


def test_execution_briefing(temp_qla_env):
    exec_engine: ExecutionEngine = temp_qla_env["exec_engine"]

    briefing = exec_engine.get_morning_briefing()
    assert "GOOD MORNING" in briefing["greeting"]
    assert len(briefing["top_5_critical_actions_today"]) == 5

    # Milestone tracking
    milestones = exec_engine.initialize_deal_critical_path(deal_id="test_deal_1")
    assert len(milestones) == 11
    assert milestones[0].title.startswith("1. Identify")


@pytest.mark.asyncio
async def test_qla_tools_execution():
    tools = ToolRegistry()
    tools.register(QLADealFlowTool())
    tools.register(QLAFinancialAnalysisTool())
    tools.register(QLADreamTeamTool())
    tools.register(QLAFinancingTool())
    tools.register(QLANegotiationTool())
    tools.register(QLAExecutionTool())

    # 1. Test deal flow tool
    res = await tools.execute(
        "qla_deal_flow",
        {
            "action": "add",
            "company_name": "Metro Plumbing Group",
            "industry": "Commercial Plumbing",
            "revenue": 3_500_000.0,
            "ebitda": 700_000.0,
            "asking_price": 2_800_000.0,
        },
    )
    assert res.success is True
    assert "Metro Plumbing Group" in res.output

    # 2. Test financial tool
    res_fin = await tools.execute(
        "qla_financial_analysis",
        {
            "mode": "lbo_model",
            "purchase_price": 2_800_000.0,
            "ebitda": 700_000.0,
            "seller_note_pct": 0.30,
        },
    )
    assert res_fin.success is True
    assert "Senior Debt" in res_fin.output

    # 3. Test execution tool
    res_exec = await tools.execute("qla_execution", {"action": "morning_briefing"})
    assert res_exec.success is True
    assert "TOP 5 CRITICAL ACTIONS" in res_exec.output


@pytest.mark.asyncio
async def test_quantum_leap_agent_master_personality():
    mock_model = MockModelAdapter(model_name="mock-qla-model")
    tools = ToolRegistry()
    tools.register(QLADealFlowTool())
    tools.register(QLAFinancialAnalysisTool())

    agent = QuantumLeapAgent(model=mock_model, tools=tools)
    assert agent.name == "quantum_leap"
    assert "qla_deal_flow" in agent.allowed_tools
    assert "qla_financial_analysis" in agent.allowed_tools

    # Preset mock response to verify 6-point QLA Action Checkpoint
    checkpoint_response = (
        "The proposed transaction is viable provided we structure 30% seller financing.\n\n"
        "--- QLA ACTION CHECKPOINT ---\n"
        "1. WHAT HAVE WE ESTABLISHED? Target does $3M revenue, $600k EBITDA.\n"
        "2. WHAT REMAINS UNKNOWN? Verified filed tax returns.\n"
        "3. WHAT DECISION MUST BE MADE? Counter at 4.0x EBITDA ($2.4M).\n"
        "4. WHAT ACTION HAPPENS NEXT? Issue non-binding indicative terms.\n"
        "5. WHO IS ACCOUNTABLE? Acquisition Lead.\n"
        "6. WHEN WILL IT BE COMPLETED? Friday at 5:00 PM."
    )
    mock_model.preset_responses["evaluate this deal"] = checkpoint_response

    from onyx.agents.base import AgentTask
    task = AgentTask(goal="evaluate this deal", assigned_agent="quantum_leap")
    result_task = await agent.execute_task(task)

    assert result_task.status.value == "completed"
    assert "--- QLA ACTION CHECKPOINT ---" in result_task.result
    assert "WHAT HAVE WE ESTABLISHED?" in result_task.result
    assert "WHEN WILL IT BE COMPLETED?" in result_task.result
