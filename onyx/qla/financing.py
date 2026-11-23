"""Financing Engine - Capital stack analysis, lender database, and financing memorandum synthesis."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from onyx.qla.models import LenderRecord, LenderType


class FinancingEngine:
    """Manages lender relations, capital debt capacity, and institutional financing packages."""

    def __init__(self, storage_path: str = "data/qla/lenders.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.lenders: Dict[str, LenderRecord] = {}
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                for item in data:
                    rec = LenderRecord(**item)
                    self.lenders[rec.id] = rec
            except Exception:
                self.lenders = {}
        else:
            self._seed_default_lenders()

    def _save(self) -> None:
        data = [l.to_dict() for l in self.lenders.values()]
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _seed_default_lenders(self) -> None:
        default_lenders = [
            LenderRecord(
                institution_name="Middle Market Commercial Bank (Tier 1)",
                lender_type=LenderType.COMMERCIAL_BANK,
                typical_deal_min=2_000_000.0,
                typical_deal_max=35_000_000.0,
                max_leverage_ebitda=3.5,
                min_dscr=1.30,
                security_requirements="1st senior lien on AR, inventory, machinery, and real estate",
                preferred_industries=["Healthcare", "HVAC", "Manufacturing", "Distribution"],
                notes="Requires audited financials (3 yrs) and experienced board presence.",
            ),
            LenderRecord(
                institution_name="Private Credit & Asset-Based Senior Fund",
                lender_type=LenderType.ASSET_BASED,
                typical_deal_min=1_500_000.0,
                typical_deal_max=20_000_000.0,
                max_leverage_ebitda=4.0,
                min_dscr=1.20,
                security_requirements="Senior blanket lien with 85% advance on eligible AR",
                preferred_industries=["Essential Services", "Commercial Facilities", "Industrial"],
                notes="Flexible covenants, higher pricing (SOFR + 550-700 bps).",
            ),
            LenderRecord(
                institution_name="Subordinated Mezzanine Capital Partners",
                lender_type=LenderType.MEZZANINE,
                typical_deal_min=1_000_000.0,
                typical_deal_max=15_000_000.0,
                max_leverage_ebitda=5.0,
                min_dscr=1.15,
                security_requirements="2nd subordinate lien, equity warrants (2-5%)",
                preferred_industries=["All fragmented cash-flowing sectors"],
                notes="Fills equity gaps between senior debt and seller note.",
            ),
        ]
        for l in default_lenders:
            self.lenders[l.id] = l
        self._save()

    def add_lender(
        self,
        institution_name: str,
        lender_type: LenderType,
        typical_deal_min: float,
        typical_deal_max: float,
        max_leverage_ebitda: float = 3.5,
        min_dscr: float = 1.25,
        security_requirements: str = "",
        preferred_industries: Optional[List[str]] = None,
        contact_info: str = "",
        notes: str = "",
    ) -> LenderRecord:
        lender = LenderRecord(
            institution_name=institution_name,
            lender_type=lender_type,
            typical_deal_min=float(typical_deal_min),
            typical_deal_max=float(typical_deal_max),
            max_leverage_ebitda=float(max_leverage_ebitda),
            min_dscr=float(min_dscr),
            security_requirements=security_requirements,
            preferred_industries=preferred_industries or [],
            contact_info=contact_info,
            notes=notes,
        )
        self.lenders[lender.id] = lender
        self._save()
        return lender

    def match_lenders(self, target_ebitda: float, loan_amount_needed: float, industry: str) -> List[Dict[str, Any]]:
        """Filter and rank financing sources by leverage tolerance and ticket size."""
        matches = []
        for l in self.lenders.values():
            max_capacity = target_ebitda * l.max_leverage_ebitda
            size_fits = (l.typical_deal_min <= loan_amount_needed <= l.typical_deal_max)
            industry_fits = any(ind.lower() in industry.lower() for ind in l.preferred_industries) or not l.preferred_industries

            if size_fits and max_capacity >= loan_amount_needed:
                matches.append({
                    "lender_id": l.id,
                    "institution_name": l.institution_name,
                    "lender_type": l.lender_type.value if hasattr(l.lender_type, "value") else l.lender_type,
                    "max_leverage_capacity": round(max_capacity, 2),
                    "min_dscr_required": l.min_dscr,
                    "security_requirements": l.security_requirements,
                    "fit_rating": "High" if industry_fits else "Moderate",
                })
        return sorted(matches, key=lambda x: x["max_leverage_capacity"], reverse=True)

    def generate_financing_memorandum_structure(
        self,
        company_name: str,
        industry: str,
        revenue: float,
        ebitda: float,
        purchase_price: float,
        debt_requested: float,
        seller_note_offered: float,
    ) -> Dict[str, Any]:
        """Produce the standard QLA bank financing memorandum outline."""
        return {
            "title": f"CONFIDENTIAL ACQUISITION FINANCING MEMORANDUM: {company_name}",
            "sections": [
                {
                    "section": "1. Executive Summary & Transaction Overview",
                    "content": f"Platform acquisition of {company_name} ({industry}). Total enterprise valuation ${purchase_price:,.0f} ({purchase_price/max(1, ebitda):.2f}x EBITDA). Senior debt request: ${debt_requested:,.0f}.",
                },
                {
                    "section": "2. Sources and Uses of Funds",
                    "sources": {
                        "Senior Commercial Debt": f"${debt_requested:,.0f} ({(debt_requested/purchase_price)*100:.1f}%)",
                        "Subordinated Seller Note": f"${seller_note_offered:,.0f} ({(seller_note_offered/purchase_price)*100:.1f}%)",
                        "Platform / Rollover Equity (OPM)": f"${max(0.0, purchase_price - debt_requested - seller_note_offered):,.0f}",
                    },
                    "uses": {
                        "Purchase Price to Seller": f"${purchase_price:,.0f}",
                        "Working Capital Injection": "Funded from target accounts receivable",
                        "Professional Legal & Accounting Fees": "Deferred to close, paid from closing proceeds",
                    },
                },
                {
                    "section": "3. Historical Financial Summary (3-5 Years)",
                    "content": f"Verified Revenue: ${revenue:,.0f} | Normalized EBITDA: ${ebitda:,.0f} (Margin: {(ebitda/max(1, revenue))*100:.1f}%).",
                },
                {
                    "section": "4. Board Governance & Leadership Credibility",
                    "content": "Blue-ribbon Board of Directors including retired Big 4 accounting partner and top-tier M&A counsel.",
                },
                {
                    "section": "5. Collateral Security & Debt Amortization",
                    "content": "First senior security interest in all physical machinery, equipment, receivables, and company stock.",
                },
            ],
            "banker_stress_questions_rehearsal": [
                "Q: How will the business operate when the founder steps down? (A: Operating management is retained under long-term employment contracts with performance bonuses).",
                "Q: What happens if industry revenue contracts by 15%? (A: Even with a 20% revenue drop, DSCR remains above 1.20x; variable overhead can be curtailed immediately).",
                "Q: Why should our bank finance an entrepreneur without a personal guarantee? (A: Because you are lending against the audited, unencumbered balance sheet and 5-year operating track record of the target company, guided by our heavyweight board).",
            ],
        }
