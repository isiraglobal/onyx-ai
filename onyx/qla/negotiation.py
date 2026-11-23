"""Negotiation Engine - Counterparty profiling, objection annihilation, and transaction structuring."""

from typing import Dict, List, Optional, Any


class NegotiationEngine:
    """Prepares negotiation strategies, models 'price vs terms' alternatives, and conducts adversarial simulations."""

    @staticmethod
    def prepare_negotiation_brief(
        company_name: str,
        asking_price: float,
        ebitda: float,
        seller_motivation: str,
        seller_stated_terms: str = "All cash at closing",
    ) -> Dict[str, Any]:
        """Synthesize a complete negotiation battle plan."""
        ebitda = float(ebitda)
        asking_price = float(asking_price)
        implied_mult = (asking_price / ebitda) if ebitda > 0 else 0.0

        # Target outcome: 3.5x to 4.5x EBITDA, 30-40% seller financed
        target_valuation = ebitda * 4.0
        target_cash_at_close = target_valuation * 0.60
        target_seller_note = target_valuation * 0.40

        # Walk-away conditions
        walk_away = [
            "Asking price exceeds 5.5x EBITDA without substantial hard asset backing",
            "Seller demands personal guarantee from buyer",
            "Seller refuses to provide 3 years of audited tax returns",
            "Seller demands 100% all-cash at close without indemnification escrow",
            "Single customer represents > 25% of annual revenue with no multi-year lock-in",
        ]

        # Alternative Deal Structures: "You name the price, I name the terms"
        alternative_structures = [
            {
                "structure_name": "Full Asking Price via Long-Term Seller Note",
                "rationale": "Grant the seller their ego/headline price ($" + f"{asking_price:,.0f}" + "), but subordinate 50-60% into a 7-year note at 4-5% interest.",
                "cash_at_close": f"${asking_price * 0.45:,.0f} (Bank Debt)",
                "seller_financing": f"${asking_price * 0.55:,.0f} (7-yr amortizing note)",
                "buyer_benefit": "Zero cash out of pocket; annual debt service is easily covered by target cash flow.",
            },
            {
                "structure_name": "Standard QLA LBO (Senior Debt + Seller Note)",
                "rationale": "Fair market valuation (4.0x EBITDA) with clean division between bank debt and seller note.",
                "cash_at_close": f"${target_cash_at_close:,.0f}",
                "seller_financing": f"${target_seller_note:,.0f} (5-yr note at 6%)",
                "buyer_benefit": "Comfortable 1.45x DSCR coverage and rapid equity buildup.",
            },
            {
                "structure_name": "Earnout / Performance-Linked Bridge",
                "rationale": "Pay 3.5x upfront cash, with remaining valuation paid only if client retention exceeds 90% over 24 months.",
                "cash_at_close": f"${ebitda * 3.5:,.0f}",
                "seller_financing": "Contingent earnout based on gross profit targets",
                "buyer_benefit": "Protects against post-acquisition customer churn.",
            },
        ]

        # Objections & High-Ticket Doctor Responses
        objection_playbook = {
            "I have another buyer offering all cash": (
                "Challenge: 'John, financial buyers make promises every day. Have they shown you a firm commitment letter from a commercial lender, "
                "or are they going to tie your company up in 90 days of exclusivity only to re-trade your price down 25%? Our board consists of retired Big 4 partners; "
                "when we issue a Letter of Intent, we close. Do you want certainty of closing, or do you want to gamble with tire-kickers?'"
            ),
            "I want all cash at closing, no seller note": (
                "Response: 'Mr. Seller, in every middle-market M&A transaction, a seller note is the standard bridge demonstrating your confidence in the company you built. "
                "No commercial bank will fund 100% cash without seller skin in the game. You name the price, or you name the terms. If you want 100% cash today, our valuation multiple is 3.0x EBITDA. "
                "If you want your full headline price, you must provide a 5-year subordinated note. Which is more important to your family: headline price or instant liquidity?'"
            ),
            "I need to think about it": (
                "Disqualify: 'John, usually when someone says they have to think about it, what they really mean is no. Be completely honest with me — "
                "is there a fundamental mismatch here, or are you just trying to be polite? If it's not a fit, let's part as friends today so neither of us wastes time.'"
            ),
        }

        return {
            "company_name": company_name,
            "headline_asking_price": asking_price,
            "implied_ebitda_multiple": round(implied_mult, 2),
            "seller_motivation": seller_motivation,
            "target_valuation": round(target_valuation, 2),
            "walk_away_conditions": walk_away,
            "alternative_structures": alternative_structures,
            "objection_playbook": objection_playbook,
            "closing_strategy": "Draft Letter of Intent (LOI) with 45-day exclusivity, 60-day closing target, and 10% escrow holdback.",
        }

    @staticmethod
    def simulate_seller_pushback(user_offer_summary: str) -> Dict[str, str]:
        """Simulate a tough, skeptical middle-market business owner response."""
        return {
            "seller_persona": "62-year-old founder, built business over 28 years, emotionally attached, skeptical of buyers without cash",
            "seller_response": (
                "Look, I've spent nearly 30 years building this business with sweat and blood. You're coming in here talking about commercial bank debt, "
                "board directors, and having ME finance a third of the purchase price over 5 years?! If I wanted to stay in the lending business, I'd open a bank! "
                "Why shouldn't I just wait for a private equity group that will write me a check for the whole thing on day one?"
            ),
            "jarvis_coaching": (
                "DO NOT BACK DOWN OR APOLOGIZE! Point out that PE firms will gut his workforce, demand 2-year transition earnouts, and re-trade the price during diligence. "
                "Remind him that your board preserves his company's legacy and employees, while the seller note gives him high-yielding guaranteed quarterly interest income "
                "sheltered from immediate capital gains tax."
            ),
        }
