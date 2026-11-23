"""Deterministic Financial Analysis, LBO Modeling, and Bogus Financial Books Verification."""

from typing import Dict, List, Optional, Any


class FinancialAnalysisEngine:
    """Performs deterministic financial ratio calculations, LBO capital structuring, and fraud audits."""

    @staticmethod
    def calculate_ratios(
        revenue: float,
        ebitda: float,
        cogs: Optional[float] = None,
        total_debt: float = 0.0,
        cash: float = 0.0,
        annual_debt_service: float = 0.0,
        current_assets: Optional[float] = None,
        current_liabilities: Optional[float] = None,
        owner_salary_addback: float = 0.0,
        discretionary_expenses: float = 0.0,
    ) -> Dict[str, Any]:
        """Compute key operational and financial ratios deterministically."""
        revenue = float(revenue)
        ebitda = float(ebitda)

        ebitda_margin = (ebitda / revenue * 100.0) if revenue > 0 else 0.0
        gross_profit = (revenue - float(cogs)) if cogs is not None else None
        gross_margin = (gross_profit / revenue * 100.0) if (gross_profit is not None and revenue > 0) else None

        net_debt = float(total_debt) - float(cash)
        working_capital = (float(current_assets) - float(current_liabilities)) if (current_assets is not None and current_liabilities is not None) else None

        # Normalized Seller Discretionary Earnings (SDE)
        normalized_earnings = ebitda + float(owner_salary_addback) + float(discretionary_expenses)

        # Debt Service Coverage Ratio (DSCR) = EBITDA / Annual Debt Service
        dscr = (ebitda / float(annual_debt_service)) if float(annual_debt_service) > 0 else None

        return {
            "revenue": revenue,
            "ebitda": ebitda,
            "ebitda_margin_pct": round(ebitda_margin, 2),
            "gross_profit": round(gross_profit, 2) if gross_profit is not None else None,
            "gross_margin_pct": round(gross_margin, 2) if gross_margin is not None else None,
            "net_debt": round(net_debt, 2),
            "working_capital": round(working_capital, 2) if working_capital is not None else None,
            "normalized_earnings": round(normalized_earnings, 2),
            "debt_service_coverage_ratio": round(dscr, 2) if dscr is not None else None,
            "dscr_health": (
                "Excellent (>= 1.5x)" if (dscr and dscr >= 1.5)
                else "Acceptable (1.25x - 1.49x)" if (dscr and dscr >= 1.25)
                else "High Risk (< 1.25x)" if dscr
                else "No Debt Service Specified"
            ),
        }

    @staticmethod
    def model_lbo_structure(
        purchase_price: float,
        ebitda: float,
        senior_debt_multiple: float = 3.0,
        senior_interest_rate: float = 0.075,
        senior_term_years: int = 7,
        seller_note_pct: float = 0.25,
        seller_interest_rate: float = 0.06,
        seller_term_years: int = 5,
    ) -> Dict[str, Any]:
        """Model an LBO capital structure combining Senior Commercial Debt, Seller Note, and Rollover/OPM Equity.

        QLA Rule: Minimize or eliminate personal cash; maximize debt supported strictly by target assets and cash flow.
        """
        purchase_price = float(purchase_price)
        ebitda = float(ebitda)

        # Max Senior Debt capacity based on leverage multiple
        max_senior_debt = ebitda * senior_debt_multiple
        senior_debt = min(max_senior_debt, purchase_price * 0.70)

        # Annual amortizing debt service for senior loan (standard PMT formula approximation)
        r_sr = senior_interest_rate
        n_sr = senior_term_years
        if r_sr > 0 and n_sr > 0:
            senior_annual_service = senior_debt * (r_sr * (1 + r_sr) ** n_sr) / ((1 + r_sr) ** n_sr - 1)
        else:
            senior_annual_service = senior_debt / max(1, n_sr)

        # Seller Financing Note
        seller_note = purchase_price * seller_note_pct
        r_sl = seller_interest_rate
        n_sl = seller_term_years
        if r_sl > 0 and n_sl > 0:
            seller_annual_service = seller_note * (r_sl * (1 + r_sl) ** n_sl) / ((1 + r_sl) ** n_sl - 1)
        else:
            seller_annual_service = seller_note / max(1, n_sl)

        total_annual_debt_service = senior_annual_service + seller_annual_service
        total_debt_funded = senior_debt + seller_note
        equity_gap = max(0.0, purchase_price - total_debt_funded)

        dscr = (ebitda / total_annual_debt_service) if total_annual_debt_service > 0 else 0.0

        # Downside stress testing scenarios (revenue or EBITDA drops by 10%, 20%, 30%)
        stress_scenarios = {}
        for drop_pct in [10, 20, 30]:
            stressed_ebitda = ebitda * (1.0 - drop_pct / 100.0)
            stressed_dscr = stressed_ebitda / total_annual_debt_service if total_annual_debt_service > 0 else 0.0
            stress_scenarios[f"ebitda_down_{drop_pct}pct"] = {
                "stressed_ebitda": round(stressed_ebitda, 2),
                "stressed_dscr": round(stressed_dscr, 2),
                "solvency_verdict": "Viable" if stressed_dscr >= 1.15 else "Breach / Danger Zone",
            }

        return {
            "purchase_price": purchase_price,
            "ebitda": ebitda,
            "implied_valuation_multiple": round(purchase_price / ebitda, 2) if ebitda > 0 else 0.0,
            "senior_debt": round(senior_debt, 2),
            "senior_debt_pct": round((senior_debt / purchase_price) * 100, 1),
            "senior_annual_debt_service": round(senior_annual_service, 2),
            "seller_note": round(seller_note, 2),
            "seller_note_pct": round((seller_note / purchase_price) * 100, 1),
            "seller_annual_debt_service": round(seller_annual_service, 2),
            "total_debt_funded": round(total_debt_funded, 2),
            "equity_opm_required": round(equity_gap, 2),
            "equity_pct": round((equity_gap / purchase_price) * 100, 1),
            "total_annual_debt_service": round(total_annual_debt_service, 2),
            "base_dscr": round(dscr, 2),
            "dscr_verdict": "Financially Viable" if dscr >= 1.25 else "Under-capitalized / Insufficient Coverage",
            "downside_stress_tests": stress_scenarios,
        }

    @staticmethod
    def audit_bogus_financial_books(
        has_tax_returns: bool,
        tax_return_revenue: Optional[float],
        reported_pl_revenue: float,
        largest_customer_pct: float,
        top_3_customers_pct: float,
        largest_supplier_pct: float,
        owner_actively_runs_daily_ops: bool,
        years_of_financial_records: int,
        unbilled_ar_pct: float = 0.0,
        has_unrecorded_liabilities_history: bool = False,
    ) -> Dict[str, Any]:
        """Examine financial records for discrepancies, fraud risks, and misrepresentation.

        Inspired by Dan Peña's 'Bogus Financial Books - Dan Responds to Bullshit' doctrine:
        - Cross-examine internal management P&L against IRS / tax returns filed.
        - Uncover customer concentration death traps.
        - Assess owner key-man operational dependency.
        """
        red_flags: List[str] = []
        warnings: List[str] = []
        risk_score = 0  # 0 to 100

        # 1. Tax Returns vs P&L
        if not has_tax_returns:
            red_flags.append("CRITICAL: Seller has NOT provided filed corporate tax returns. Unverified numbers!")
            risk_score += 40
        elif tax_return_revenue is not None and reported_pl_revenue > 0:
            diff_pct = abs(reported_pl_revenue - tax_return_revenue) / reported_pl_revenue * 100.0
            if diff_pct > 15.0:
                red_flags.append(
                    f"MAJOR DISCREPANCY: Reported P&L revenue (${reported_pl_revenue:,.0f}) differs by "
                    f"{diff_pct:.1f}% from filed tax returns (${tax_return_revenue:,.0f}). Possible bogus books or tax evasion!"
                )
                risk_score += 35
            elif diff_pct > 5.0:
                warnings.append(f"Minor discrepancy ({diff_pct:.1f}%) between tax return and internal P&L.")
                risk_score += 10

        # 2. Customer Concentration
        if largest_customer_pct >= 25.0:
            red_flags.append(
                f"CUSTOMER CONCENTRATION DANGER: Largest single customer accounts for {largest_customer_pct:.1f}% of revenue! "
                "Losing one client destroys company cash flow and debt service."
            )
            risk_score += 25
        elif largest_customer_pct >= 15.0:
            warnings.append(f"Elevated customer concentration: Largest client is {largest_customer_pct:.1f}%.")
            risk_score += 10

        if top_3_customers_pct >= 50.0:
            warnings.append(f"High top-3 client concentration: {top_3_customers_pct:.1f}% of total sales.")
            risk_score += 15

        # 3. Supplier Concentration
        if largest_supplier_pct >= 40.0:
            warnings.append(f"Supplier dependency: Largest supplier controls {largest_supplier_pct:.1f}% of COGS.")
            risk_score += 10

        # 4. Key-man / Owner Operational Dependency
        if owner_actively_runs_daily_ops:
            warnings.append(
                "OWNER DEPENDENCY: The owner is the primary salesperson or key operational operator. "
                "Business value may evaporate upon seller departure unless management retention agreement is locked."
            )
            risk_score += 15

        # 5. Historical Track Record
        if years_of_financial_records < 3:
            red_flags.append(f"INSUFFICIENT HISTORY: Only {years_of_financial_records} year(s) of records available. Banks demand minimum 3-5 years.")
            risk_score += 20

        # 6. Unbilled AR / Receivables quality
        if unbilled_ar_pct > 20.0:
            warnings.append(f"High unbilled receivables ({unbilled_ar_pct:.1f}% of AR). Risk of bad debt write-offs.")
            risk_score += 10

        # 7. Unrecorded liabilities
        if has_unrecorded_liabilities_history:
            red_flags.append("HISTORY OF UNRECORDED LIABILITIES: Pending labor claims, tax liens, or warranty disputes.")
            risk_score += 25

        risk_score = min(100, risk_score)
        recommendation = (
            "REJECT / HALT: Severe fraud or structural risks detected. Do not issue binding LOI."
            if risk_score >= 60
            else "PROCEED WITH DEEP FORENSIC DILIGENCE: Demand Quality of Earnings (QofE) report and escrow holdback."
            if risk_score >= 30
            else "CLEAN DILIGENCE PROFILE: Standard verification checks apply."
        )

        return {
            "bogus_books_risk_score": risk_score,
            "risk_rating": "CRITICAL RISK" if risk_score >= 60 else "MODERATE RISK" if risk_score >= 30 else "LOW RISK",
            "red_flags": red_flags,
            "warnings": warnings,
            "recommendation": recommendation,
            "mandatory_diligence_actions": [
                "Obtain IRS Form 4506-C directly from the government to verify filed tax returns",
                "Require seller to provide 36 consecutive months of business bank statements",
                "Audit Top 10 customer contracts for assignment clauses upon change of control",
                "Engage Big 4 / top-tier accounting firm to run Quality of Earnings (QofE) analysis on deferred fee",
            ],
        }
