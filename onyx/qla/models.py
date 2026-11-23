"""Data models and schemas for Quantum Leap Advantage (QLA) Deal-Making System."""

from dataclasses import dataclass, field, asdict
from enum import Enum
import time
from typing import Dict, List, Optional, Any
import uuid


class DealStage(str, Enum):
    IDENTIFIED = "Identified"
    CONTACTED = "Contacted"
    INFO_REQUESTED = "Information requested"
    FINANCIAL_SCREENING = "Financial screening"
    QUALIFIED = "Qualified"
    LOI = "Letter of intent"
    DUE_DILIGENCE = "Due diligence"
    FINANCING = "Financing"
    NEGOTIATION = "Negotiation"
    CLOSING = "Closing"
    TERMINATED = "Terminated"


class SourceConfidence(str, Enum):
    LEVEL_A = "Level A: Direct source material"
    LEVEL_B = "Level B: Independently verified published material"
    LEVEL_C = "Level C: Credible secondary commentary"
    LEVEL_D = "Level D: AI-generated interpretation"
    LEVEL_E = "Level E: Unverified hypothesis"


class DreamTeamRole(str, Enum):
    CHAIRMAN = "Chairman"
    BOARD_DIRECTOR = "Board Director"
    CEO = "CEO"
    CFO = "CFO"
    MA_LAWYER = "M&A Lawyer"
    CORPORATE_LAWYER = "Corporate Lawyer"
    TAX_ADVISER = "Tax Adviser"
    ACCOUNTANT = "Accountant (Big 4 / Top-Tier)"
    INVESTMENT_BANKER = "Investment Banker"
    COMMERCIAL_BANKER = "Commercial Banker"
    INDUSTRY_EXPERT = "Industry Expert"
    OPERATIONS_EXEC = "Operations Executive"
    INTEGRATION_MGR = "Integration Manager"


class CandidateStatus(str, Enum):
    IDENTIFIED = "Identified"
    CONTACTED = "Contacted"
    INTERVIEWED = "Interviewed"
    COMMITTED = "Committed"
    DECLINED = "Declined"


class LenderType(str, Enum):
    COMMERCIAL_BANK = "Commercial Bank"
    ASSET_BASED = "Asset-Based Lender"
    MEZZANINE = "Mezzanine Debt"
    PRIVATE_CREDIT = "Private Credit"
    FAMILY_OFFICE = "Family Office"
    SELLER_FINANCE = "Seller Financing"


class MilestoneStatus(str, Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    BLOCKED = "Blocked"
    COMPLETED = "Completed"


@dataclass
class DealOpportunity:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    company_name: str = ""
    website: str = ""
    industry: str = ""
    location: str = ""
    revenue: float = 0.0                      # Annualized verified or reported revenue
    ebitda: float = 0.0                       # Annualized EBITDA
    asking_price: float = 0.0                 # Seller asking price
    ownership_structure: str = ""             # Sole proprietor, 50/50 partnership, PE-backed, etc.
    seller_motivation: str = ""               # Retirement, succession gap, burnout, health
    source_of_intro: str = ""                 # Broker, cold outreach, joint venture partner, banker
    contact_person: str = ""                  # Primary owner or broker
    last_communication: str = ""              # Date/notes of last contact
    next_action: str = ""                     # Strict next action with deadline
    confidence_rating: str = SourceConfidence.LEVEL_E.value
    outstanding_diligence: List[str] = field(default_factory=list)
    status: DealStage = DealStage.IDENTIFIED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value if isinstance(self.status, DealStage) else self.status
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DealOpportunity":
        status_raw = data.get("status", DealStage.IDENTIFIED.value)
        try:
            status = DealStage(status_raw)
        except ValueError:
            status = DealStage.IDENTIFIED
        copy_data = dict(data)
        copy_data["status"] = status
        return cls(**copy_data)


@dataclass
class DreamTeamCandidate:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    role: DreamTeamRole = DreamTeamRole.BOARD_DIRECTOR
    background: str = ""
    credentials: str = ""                     # e.g., "Retired Partner PwC, 32 yrs M&A audit"
    transaction_history: str = ""             # Closed $500M+ in middle market transactions
    industry_experience: str = ""             # 25 years in healthcare / HVAC
    references: List[str] = field(default_factory=list)
    compensation_terms: str = "1-2% equity at platform close, no out-of-pocket retainer"
    status: CandidateStatus = CandidateStatus.IDENTIFIED
    contact_info: str = ""
    notes: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["role"] = self.role.value if isinstance(self.role, DreamTeamRole) else self.role
        data["status"] = self.status.value if isinstance(self.status, CandidateStatus) else self.status
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DreamTeamCandidate":
        role_raw = data.get("role", DreamTeamRole.BOARD_DIRECTOR.value)
        status_raw = data.get("status", CandidateStatus.IDENTIFIED.value)
        try:
            role = DreamTeamRole(role_raw)
        except ValueError:
            role = DreamTeamRole.BOARD_DIRECTOR
        try:
            status = CandidateStatus(status_raw)
        except ValueError:
            status = CandidateStatus.IDENTIFIED
        copy_data = dict(data)
        copy_data["role"] = role
        copy_data["status"] = status
        return cls(**copy_data)


@dataclass
class LenderRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    institution_name: str = ""
    lender_type: LenderType = LenderType.COMMERCIAL_BANK
    typical_deal_min: float = 1_000_000.0
    typical_deal_max: float = 25_000_000.0
    max_leverage_ebitda: float = 3.5          # Maximum senior debt / EBITDA multiple
    min_dscr: float = 1.25                    # Minimum Debt Service Coverage Ratio
    security_requirements: str = "Senior lien on all business assets, receivables, equipment"
    preferred_industries: List[str] = field(default_factory=list)
    contact_info: str = ""
    interaction_history: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["lender_type"] = self.lender_type.value if isinstance(self.lender_type, LenderType) else self.lender_type
        return data


@dataclass
class CriticalPathMilestone:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    deal_id: str = ""
    title: str = ""
    stage: str = ""
    assigned_to: str = "You (Acquisition Lead)"
    due_date: str = ""
    status: MilestoneStatus = MilestoneStatus.PENDING
    blocker_reason: Optional[str] = None
    verified_evidence: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value if isinstance(self.status, MilestoneStatus) else self.status
        return data
