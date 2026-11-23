"""Deal Flow Engine - Pipeline management, sourcing, and opportunity qualification."""

import json
import os
from pathlib import Path
import time
from typing import Dict, List, Optional, Any
from onyx.qla.models import DealOpportunity, DealStage, SourceConfidence


class DealFlowEngine:
    """Manages the end-to-end M&A deal pipeline for QLA acquisitions."""

    def __init__(self, storage_path: str = "data/qla/deals.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.deals: Dict[str, DealOpportunity] = {}
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                for item in data:
                    deal = DealOpportunity.from_dict(item)
                    self.deals[deal.id] = deal
            except Exception:
                self.deals = {}

    def _save(self) -> None:
        data = [deal.to_dict() for deal in self.deals.values()]
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_opportunity(
        self,
        company_name: str,
        industry: str,
        revenue: float,
        ebitda: float,
        asking_price: float,
        location: str = "",
        website: str = "",
        seller_motivation: str = "",
        source_of_intro: str = "Direct owner outreach",
        contact_person: str = "",
        next_action: str = "Request last 3 years of P&L and tax returns",
        confidence_rating: str = SourceConfidence.LEVEL_C.value,
        notes: str = "",
    ) -> DealOpportunity:
        """Register a new acquisition target into the deal pipeline."""
        deal = DealOpportunity(
            company_name=company_name,
            industry=industry,
            revenue=float(revenue),
            ebitda=float(ebitda),
            asking_price=float(asking_price),
            location=location,
            website=website,
            seller_motivation=seller_motivation,
            source_of_intro=source_of_intro,
            contact_person=contact_person,
            next_action=next_action,
            confidence_rating=confidence_rating,
            notes=notes,
            status=DealStage.IDENTIFIED,
        )
        self.deals[deal.id] = deal
        self._save()
        return deal

    def update_stage(self, deal_id: str, new_stage: DealStage, next_action: Optional[str] = None) -> Optional[DealOpportunity]:
        """Advance or transition an opportunity to a new pipeline stage."""
        if deal_id not in self.deals:
            return None
        deal = self.deals[deal_id]
        deal.status = new_stage
        deal.updated_at = time.time()
        if next_action:
            deal.next_action = next_action
        self._save()
        return deal

    def get_deal(self, deal_id: str) -> Optional[DealOpportunity]:
        return self.deals.get(deal_id)

    def list_deals(
        self,
        stage: Optional[DealStage] = None,
        industry: Optional[str] = None,
    ) -> List[DealOpportunity]:
        results = list(self.deals.values())
        if stage:
            results = [d for d in results if d.status == stage]
        if industry:
            results = [d for d in results if industry.lower() in d.industry.lower()]
        return sorted(results, key=lambda d: d.updated_at, reverse=True)

    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Generate high-level deal flow metrics and distribution across stages."""
        summary = {stage.value: 0 for stage in DealStage}
        total_pipeline_value = 0.0
        total_ebitda = 0.0

        for deal in self.deals.values():
            if deal.status != DealStage.TERMINATED:
                summary[deal.status.value] = summary.get(deal.status.value, 0) + 1
                total_pipeline_value += deal.asking_price or deal.revenue
                total_ebitda += deal.ebitda

        active_count = sum(c for st, c in summary.items() if st != DealStage.TERMINATED.value)

        return {
            "total_active_opportunities": active_count,
            "total_pipeline_value": round(total_pipeline_value, 2),
            "total_pipeline_ebitda": round(total_ebitda, 2),
            "stages_breakdown": summary,
            "qualified_count": summary.get(DealStage.QUALIFIED.value, 0),
            "active_diligence_count": summary.get(DealStage.DUE_DILIGENCE.value, 0),
            "negotiation_count": summary.get(DealStage.NEGOTIATION.value, 0),
        }

    def find_weakest_deal(self) -> Optional[Dict[str, Any]]:
        """Identify the weakest deal in the pipeline based on multiple risk indicators."""
        active = [d for d in self.deals.values() if d.status not in (DealStage.TERMINATED, DealStage.CLOSING)]
        if not active:
            return None

        scored_deals = []
        for d in active:
            flaw_score = 0
            reasons = []

            # 1. Unreasonable valuation multiple (Asking price / EBITDA > 6.0x for middle market)
            if d.ebitda > 0:
                multiple = d.asking_price / d.ebitda
                if multiple > 6.0:
                    flaw_score += 3
                    reasons.append(f"Excessive valuation multiple ({multiple:.1f}x EBITDA)")
            elif d.ebitda <= 0 and d.asking_price > 0:
                flaw_score += 5
                reasons.append("Unprofitable or zero reported EBITDA")

            # 2. EBITDA margin < 10%
            if d.revenue > 0:
                margin = (d.ebitda / d.revenue) * 100
                if margin < 10.0:
                    flaw_score += 2
                    reasons.append(f"Thin EBITDA margin ({margin:.1f}%)")

            # 3. Unverified confidence
            if d.confidence_rating in (SourceConfidence.LEVEL_E.value, SourceConfidence.LEVEL_D.value):
                flaw_score += 2
                reasons.append("Unverified figures (Source Level D/E)")

            # 4. Lack of immediate next action
            if not d.next_action or "pending" in d.next_action.lower():
                flaw_score += 2
                reasons.append("No crisp next action or accountability deadline")

            scored_deals.append({
                "deal_id": d.id,
                "company_name": d.company_name,
                "industry": d.industry,
                "status": d.status.value,
                "flaw_score": flaw_score,
                "reasons": reasons,
                "revenue": d.revenue,
                "ebitda": d.ebitda,
                "asking_price": d.asking_price,
            })

        scored_deals.sort(key=lambda x: x["flaw_score"], reverse=True)
        return scored_deals[0] if scored_deals else None
