"""Execution Engine - Critical path milestone management and daily/weekly QLA accountability."""

import json
from pathlib import Path
import time
from typing import Dict, List, Optional, Any
from onyx.qla.models import CriticalPathMilestone, MilestoneStatus
from onyx.qla.deal_flow import DealFlowEngine


class ExecutionEngine:
    """Tracks transaction critical paths, eliminates bottlenecks, and enforces daily accountability."""

    STANDARD_CRITICAL_PATH = [
        "1. Identify Fragmented Industry & Initial Target",
        "2. Conduct Preliminary Screening & Red Flag Review",
        "3. Cold Outreach / Direct Owner Contact Established",
        "4. Obtain 3-5 Years Financial Statements & Tax Returns",
        "5. Deterministic Financial & LBO Capacity Analysis Completed",
        "6. Blue-Ribbon Board of Directors & M&A Lawyer Confirmed",
        "7. Negotiate and Submit Non-Binding Letter of Intent (LOI)",
        "8. Execute Forensic Due Diligence (Quality of Earnings & Legal)",
        "9. Secure Commercial Bank Debt Commitment Letter",
        "10. Finalize Purchase Agreement & Seller Note Documentation",
        "11. Close Transaction, Fund Escrow & Initiate Day-1 Integration",
    ]

    def __init__(self, storage_path: str = "data/qla/execution.json", deal_engine: Optional[DealFlowEngine] = None):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.deal_engine = deal_engine or DealFlowEngine()
        self.milestones: Dict[str, CriticalPathMilestone] = {}
        self.daily_logs: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                for m_data in data.get("milestones", []):
                    m = CriticalPathMilestone(**m_data)
                    self.milestones[m.id] = m
                self.daily_logs = data.get("daily_logs", [])
            except Exception:
                self.milestones = {}
                self.daily_logs = []

    def _save(self) -> None:
        data = {
            "milestones": [m.to_dict() for m in self.milestones.values()],
            "daily_logs": self.daily_logs,
        }
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def initialize_deal_critical_path(self, deal_id: str) -> List[CriticalPathMilestone]:
        """Instantiate standard QLA critical path milestones for a specific deal."""
        created = []
        for step in self.STANDARD_CRITICAL_PATH:
            m = CriticalPathMilestone(
                deal_id=deal_id,
                title=step,
                stage=step.split(".")[1].strip(),
                status=MilestoneStatus.PENDING,
            )
            self.milestones[m.id] = m
            created.append(m)
        self._save()
        return created

    def update_milestone(
        self,
        milestone_id: str,
        status: MilestoneStatus,
        blocker_reason: Optional[str] = None,
        verified_evidence: Optional[str] = None,
    ) -> Optional[CriticalPathMilestone]:
        if milestone_id not in self.milestones:
            return None
        m = self.milestones[milestone_id]
        m.status = status
        if blocker_reason is not None:
            m.blocker_reason = blocker_reason
        if verified_evidence is not None:
            m.verified_evidence = verified_evidence
        self._save()
        return m

    def get_morning_briefing(self) -> Dict[str, Any]:
        """Synthesize the daily morning command briefing."""
        summary = self.deal_engine.get_pipeline_summary()
        active_deals = self.deal_engine.list_deals()

        top_actions = []
        for d in active_deals[:5]:
            if d.next_action:
                top_actions.append(f"[{d.company_name}] {d.next_action}")

        # If no deals or actions, provide default high-priority actions
        if not top_actions:
            top_actions = [
                "Target Sourcing: Call 20 business owners or brokers in your target fragmented sector",
                "Dream Team: Interview candidate for Big 4 retired accounting partner on board",
                "Financing: Meet regional commercial bank VP of commercial lending",
                "Pipeline: Review last 3 years tax returns for active target",
                "Accountability: Recite bodacious affirmations 2x today",
            ]

        blocked_milestones = [
            {"title": m.title, "deal_id": m.deal_id, "blocker": m.blocker_reason}
            for m in self.milestones.values()
            if m.status == MilestoneStatus.BLOCKED
        ]

        return {
            "greeting": "GOOD MORNING. YOUR QLA DEAL COMMAND CENTRE IS LIVE.",
            "pipeline_summary": summary,
            "top_5_critical_actions_today": top_actions[:5],
            "blocked_milestones": blocked_milestones,
            "core_mandate": "What gets measured gets accomplished. No excuses. Execute the critical path.",
        }

    def log_daily_activity(self, activity_type: str, details: str, outcome: str) -> None:
        """Log a call, meeting, negotiation, or commitment made during the day."""
        self.daily_logs.append({
            "timestamp": time.time(),
            "activity_type": activity_type,
            "details": details,
            "outcome": outcome,
        })
        self._save()

    def get_evening_review(self) -> Dict[str, Any]:
        """Conduct the end-of-day accountability review."""
        now = time.time()
        today_logs = [log for log in self.daily_logs if now - log["timestamp"] < 86400]
        summary = self.deal_engine.get_pipeline_summary()

        return {
            "activities_logged_today": len(today_logs),
            "log_entries": today_logs,
            "active_pipeline_value": summary["total_pipeline_value"],
            "accountability_audit": [
                "Did you move the critical path forward today on at least one deal?",
                "Did you speak directly with at least one owner, director, or financier?",
                "What did you fail to accomplish today, and why?",
                "What are tomorrow's top 3 non-negotiable battle priorities?",
            ],
        }

    def get_weekly_15_item_audit(self) -> Dict[str, str]:
        """Return the standard Dan Peña 15-item weekly accountability framework."""
        return {
            "1_top_accomplishment": "What was your #1 commercial accomplishment this week?",
            "2_next_week_goal": "What is your #1 goal for next week?",
            "3_deals_analyzed": "How many acquisition targets did you analyze?",
            "4_decision_makers_contacted": "How many business owners or key decision-makers did you speak with?",
            "5_pipeline_value": "What is your current total active pipeline value?",
            "6_affirmations": "Did you recite your bodacious affirmations 2x daily without fail?",
            "7_qla_study": "What specific chapters/seminars did you study from the QLA library?",
            "8_network_additions": "Who did you add to your network (high performers only)?",
            "9_uncomfortable_action": "What uncomfortable, high-friction action did you take?",
            "10_biggest_obstacle": "What is your single biggest bottleneck right now?",
            "11_laser_beam_focus_hours": "How many hours of uninterrupted laser beam focus did you log?",
            "12_pay_yourself_first": "Did you pay yourself first? (Amount and mechanism)",
            "13_exit_strategy": "What progress did you make on long-term platform exit structuring?",
            "14_accountability_partner": "Who held you accountable this week and gave you brutal truth?",
            "15_self_esteem_rating": "Rate your self-esteem from 1 to 10 and state why.",
        }
