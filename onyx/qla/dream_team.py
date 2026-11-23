"""Dream Team Engine - Board recruitment, professional adviser management, and readiness tracking."""

import json
from pathlib import Path
import time
from typing import Dict, List, Optional, Any
from onyx.qla.models import DreamTeamCandidate, DreamTeamRole, CandidateStatus


class DreamTeamEngine:
    """Manages the identification, recruitment, and onboarding of blue-ribbon Dream Team members."""

    # Essential roles that must be filled before approaching commercial banks for an LBO
    MANDATORY_CLOSING_ROLES = [
        DreamTeamRole.CHAIRMAN,
        DreamTeamRole.BOARD_DIRECTOR,
        DreamTeamRole.ACCOUNTANT,
        DreamTeamRole.MA_LAWYER,
        DreamTeamRole.COMMERCIAL_BANKER,
    ]

    def __init__(self, storage_path: str = "data/qla/dream_team.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.candidates: Dict[str, DreamTeamCandidate] = {}
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                for item in data:
                    cand = DreamTeamCandidate.from_dict(item)
                    self.candidates[cand.id] = cand
            except Exception:
                self.candidates = {}

    def _save(self) -> None:
        data = [c.to_dict() for c in self.candidates.values()]
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_candidate(
        self,
        name: str,
        role: DreamTeamRole,
        background: str,
        credentials: str,
        transaction_history: str = "",
        industry_experience: str = "",
        compensation_terms: str = "1-2% equity at platform close, no out-of-pocket retainer",
        contact_info: str = "",
        notes: str = "",
    ) -> DreamTeamCandidate:
        candidate = DreamTeamCandidate(
            name=name,
            role=role,
            background=background,
            credentials=credentials,
            transaction_history=transaction_history,
            industry_experience=industry_experience,
            compensation_terms=compensation_terms,
            contact_info=contact_info,
            notes=notes,
            status=CandidateStatus.IDENTIFIED,
        )
        self.candidates[candidate.id] = candidate
        self._save()
        return candidate

    def update_status(self, candidate_id: str, new_status: CandidateStatus) -> Optional[DreamTeamCandidate]:
        if candidate_id not in self.candidates:
            return None
        cand = self.candidates[candidate_id]
        cand.status = new_status
        self._save()
        return cand

    def get_candidate(self, candidate_id: str) -> Optional[DreamTeamCandidate]:
        return self.candidates.get(candidate_id)

    def list_candidates(
        self,
        role: Optional[DreamTeamRole] = None,
        status: Optional[CandidateStatus] = None,
    ) -> List[DreamTeamCandidate]:
        results = list(self.candidates.values())
        if role:
            results = [c for c in results if c.role == role]
        if status:
            results = [c for c in results if c.status == status]
        return sorted(results, key=lambda c: c.created_at, reverse=True)

    def assess_dream_team_readiness(self) -> Dict[str, Any]:
        """Audit the roster against mandatory QLA credibility requirements."""
        committed_roles = {
            c.role for c in self.candidates.values() if c.status == CandidateStatus.COMMITTED
        }

        missing_mandatory = [r.value for r in self.MANDATORY_CLOSING_ROLES if r not in committed_roles]
        total_committed = len([c for c in self.candidates.values() if c.status == CandidateStatus.COMMITTED])
        total_pipeline = len(self.candidates)

        readiness_pct = int(((len(self.MANDATORY_CLOSING_ROLES) - len(missing_mandatory)) / len(self.MANDATORY_CLOSING_ROLES)) * 100)

        verdict = (
            "TRANSACTION-READY: Full blue-ribbon Dream Team committed. Commercial banks will take meetings seriously."
            if not missing_mandatory
            else f"INCOMPLETE CREDIBILITY: Missing {len(missing_mandatory)} critical roles. Do NOT approach tier-1 lenders alone."
        )

        return {
            "readiness_score_pct": readiness_pct,
            "total_candidates_in_pipeline": total_pipeline,
            "total_committed_members": total_committed,
            "missing_mandatory_roles": missing_mandatory,
            "verdict": verdict,
            "next_recruitment_priority": missing_mandatory[0] if missing_mandatory else "Maintain regular board communication",
        }

    def generate_outreach_script(self, role: DreamTeamRole, target_industry: str) -> str:
        """Generate high-conviction QLA executive outreach scripts."""
        if role in (DreamTeamRole.CHAIRMAN, DreamTeamRole.BOARD_DIRECTOR):
            return (
                f"SUBJECT: Board Opportunity — Consolidation Platform in {target_industry}\n\n"
                f"Dear [Name],\n\n"
                f"I am writing to you directly because of your distinguished leadership career in {target_industry}. "
                f"Our acquisition vehicle is currently executing a disciplined roll-up of profitable, established middle-market operators in this sector.\n\n"
                f"We are assembling an elite Board of Directors to guide strategic governance, capital allocation, and M&A integration. "
                f"Rather than traditional corporate governance, we are offering significant platform equity (1-2%) to experienced industry titans who wish to create exponential value without day-to-day operational burdens.\n\n"
                f"If you are open to exploring a high-impact non-executive board seat, I would welcome 15 minutes to share our acquisition thesis and current pipeline.\n\n"
                f"Best regards,\n[Your Name]\nManaging Director, Acquisition Platform"
            )

        if role == DreamTeamRole.MA_LAWYER:
            return (
                f"SUBJECT: Engagement RFP: M&A Legal Counsel for {target_industry} Acquisition Roll-Up\n\n"
                f"Dear [Managing Partner Name],\n\n"
                f"Our corporate acquisition group is consolidating established companies within {target_industry}. "
                f"We are currently interviewing premier M&A law firms to represent our holding company across our transaction pipeline.\n\n"
                f"As is standard practice in our consolidation model, we require counsel to agree to full billing deferral to closing on a 100% success-fee basis for the initial transaction, followed by exclusive representation across all subsequent acquisitions.\n\n"
                f"With our blue-ribbon board and verified pipeline, our transactions generate recurring high-volume deal flow for our legal partners. "
                f"Please let me know if your M&A practice group has the capacity to review our platform brief this week.\n\n"
                f"Best regards,\n[Your Name]"
            )

        return (
            f"SUBJECT: Strategic Partnership — Acquisition Platform in {target_industry}\n\n"
            f"Dear [Name],\n\n"
            f"We are expanding our advisory team for a strategic acquisition platform in {target_industry}. "
            f"Given your deep transaction experience, we would like to brief you on our current targets and discuss formal advisory participation.\n\n"
            f"Best regards,\n[Your Name]"
        )
