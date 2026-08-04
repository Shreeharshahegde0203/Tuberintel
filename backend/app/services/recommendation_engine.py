from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.models import Batch, MarketPrice, QualityAssessment
from app.schemas.batches import AnalysisOptions


GRADE_FACTORS = {"A": 1.10, "B": 1.00, "C": 0.78, "D": 0.48}


@dataclass
class Candidate:
    action: str
    title: str
    market: str
    timing: str
    selling_price: float
    gross_revenue: float
    net_profit: float
    roi: float
    risk_score: float
    confidence: float
    score: float
    costs: dict[str, float]
    reasons: list[str]

    def public(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("score", None)
        return data


class RecommendationEngine:
    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
        return max(low, min(high, value))

    def evaluate(
        self,
        batch: Batch,
        assessment: QualityAssessment,
        latest_markets: list[MarketPrice],
        forecast: list[dict[str, Any]],
        options: AnalysisOptions,
    ) -> dict[str, Any]:
        is_kn = options.language == "kn"
        quintals = batch.quantity_kg / 100.0
        tonnes = batch.quantity_kg / 1000.0
        grade_factor = GRADE_FACTORS.get(assessment.quality_grade, 0.72)
        best_market = max(latest_markets, key=lambda p: p.modal_price) if latest_markets else None
        base_modal = best_market.modal_price if best_market else 2000.0
        best_market_name = best_market.market if best_market else (batch.intended_market or ("ಹತ್ತಿರದ ಸ್ಥಳೀಯ ಮಂಡಿ" if is_kn else "Nearest local mandi"))

        transport = options.distance_km * tonnes * options.transport_cost_per_km_tonne
        handling = quintals * options.handling_cost_per_quintal
        acceptance = 1.0 - assessment.rejection_probability / 100.0
        sell_price = base_modal * grade_factor

        candidates: list[Candidate] = []

        # SELL NOW
        sell_risk = self._clamp(
            assessment.rejection_probability * 0.55
            + assessment.surface_defect_severity * 0.15
            + (12 if assessment.quality_grade == "D" else 0)
        )
        sell_gross = sell_price * quintals * acceptance
        sell_costs = {"transport": transport, "handling": handling, "storage": 0.0, "processing": 0.0, "expected_loss": sell_gross * sell_risk / 100 * 0.12}
        sell_total_cost = sum(sell_costs.values())
        sell_net = sell_gross - sell_total_cost
        candidates.append(
            self._candidate(
                "SELL_NOW",
                "ಈಗಲೇ ಮಾರಾಟ ಮಾಡಿ" if is_kn else "Sell now",
                best_market_name,
                "24–48 ಗಂಟೆಗಳೊಳಗೆ" if is_kn else "Within 24–48 hours",
                sell_price,
                sell_gross,
                sell_net,
                sell_total_cost,
                sell_risk,
                assessment.confidence,
                sell_costs,
                [
                    (f"ಪ್ರಸ್ತುತ ಅತ್ಯುತ್ತಮ ಮಾದರಿ ಬೆಲೆ ಪ್ರತಿ ಕ್ವಿಂಟಲ್‌ಗೆ ಸುಮಾರು ₹{base_modal:,.0f}." if is_kn else f"Current best modal price is approximately ₹{base_modal:,.0f} per quintal."),
                    (f"ಗ್ರೇಡ್ {assessment.quality_grade} ಗೆ {grade_factor:.2f} ವಾಣಿಜ್ಯ ಗುಣಮಟ್ಟ ಗುಣಕ ಅನ್ವಯಿಸಲಾಗಿದೆ." if is_kn else f"Grade {assessment.quality_grade} applies a commercial quality factor of {grade_factor:.2f}."),
                    ("ತಕ್ಷಣದ ಮಾರಾಟವು ಸಂಗ್ರಹಣೆಯ ಗುಣಮಟ್ಟ ಕುಸಿತ ಮತ್ತು ಬೆಲೆ ಅನಿಶ್ಚಿತತೆಯನ್ನು ತಪ್ಪಿಸುತ್ತದೆ." if is_kn else "Immediate sale avoids storage deterioration and price uncertainty."),
                ],
            )
        )

        # STORE AND SELL
        storage_days = options.storage_days
        forecast_index = min(max(storage_days - 1, 0), len(forecast) - 1) if forecast else 0
        future_base = forecast[forecast_index]["predicted_price"] if forecast else base_modal * 1.04
        stored_price = future_base * grade_factor
        storage_cost = options.storage_cost_per_quintal_day * quintals * storage_days
        storage_sensitivity = (
            assessment.sprout_severity * 0.30
            + assessment.bruise_severity * 0.22
            + assessment.scab_severity * 0.16
            + assessment.discoloration_severity * 0.12
            + max(0.0, 75 - assessment.quality_score) * 0.25
        )
        storage_risk = self._clamp(10 + storage_sensitivity + storage_days * 0.55)
        stored_acceptance = max(0.35, acceptance - storage_risk / 100 * 0.18)
        store_gross = stored_price * quintals * stored_acceptance
        store_costs = {
            "transport": transport,
            "handling": handling * 1.15,
            "storage": storage_cost,
            "processing": 0.0,
            "expected_loss": store_gross * storage_risk / 100 * 0.19,
        }
        store_total = sum(store_costs.values())
        store_net = store_gross - store_total
        candidates.append(
            self._candidate(
                "STORE",
                "ಸಂಗ್ರಹಿಸಿ ನಂತರ ಮಾರಾಟ ಮಾಡಿ" if is_kn else "Store and sell later",
                best_market_name,
                (f"ಸುಮಾರು {storage_days} ದಿನಗಳ ನಂತರ" if is_kn else f"After approximately {storage_days} days"),
                stored_price,
                store_gross,
                store_net,
                store_total,
                storage_risk,
                min(assessment.confidence, 78.0),
                store_costs,
                [
                    (f"ಗ್ರೇಡ್ ಹೊಂದಾಣಿಕೆಯ ಮೊದಲು {storage_days} ದಿನಗಳ ಅಂದಾಜು ಬೆಲೆ ಪ್ರತಿ ಕ್ವಿಂಟಲ್‌ಗೆ ಸುಮಾರು ₹{future_base:,.0f}." if is_kn else f"The {storage_days}-day forecast is approximately ₹{future_base:,.0f} per quintal before grade adjustment."),
                    (f"ಈ ಲಾಟ್‌ನ ಅಂದಾಜು ಸಂಗ್ರಹ ವೆಚ್ಚ ₹{storage_cost:,.0f}." if is_kn else f"Estimated storage expense is ₹{storage_cost:,.0f} for this batch."),
                    (f"ದೃಶ್ಯ ಗುಣಮಟ್ಟ ಲಕ್ಷಣಗಳಿಂದ ಸಂಗ್ರಹ ಅಪಾಯ ಅಂಕ {storage_risk:.1f}/100 ಬಂದಿದೆ." if is_kn else f"Visible quality features produce a storage-risk score of {storage_risk:.1f}/100."),
                ],
            )
        )

        # PROCESS
        processor_base = options.processor_price_per_quintal or base_modal * 0.79
        # Processors tolerate cosmetic defects but penalize rot/greening and severe rejection risk.
        processor_quality_factor = max(0.60, 0.92 - assessment.discoloration_severity / 300 - assessment.sprout_severity / 500)
        process_price = processor_base * processor_quality_factor
        process_acceptance = max(0.62, 1.0 - assessment.rejection_probability / 180)
        process_gross = process_price * quintals * process_acceptance
        processing_logistics = handling * 1.35
        process_risk = self._clamp(16 + assessment.discoloration_severity * 0.22 + assessment.rejection_probability * 0.28)
        process_costs = {
            "transport": transport * 0.92,
            "handling": processing_logistics,
            "storage": 0.0,
            "processing": quintals * 18.0,
            "expected_loss": process_gross * process_risk / 100 * 0.08,
        }
        process_total = sum(process_costs.values())
        process_net = process_gross - process_total
        candidates.append(
            self._candidate(
                "PROCESS",
                "ಸಂಸ್ಕರಣೆಗೆ ಕಳುಹಿಸಿ" if is_kn else "Redirect to processing",
                "ಪರಿಶೀಲಿತ ಚಿಪ್ಸ್ / ಸ್ಟಾರ್ಚ್ / ಸಂಸ್ಕರಣಾ ಖರೀದಿದಾರ" if is_kn else "Verified chips / starch / processing buyer",
                "2–4 ದಿನಗಳೊಳಗೆ ರವಾನೆ" if is_kn else "Dispatch within 2–4 days",
                process_price,
                process_gross,
                process_net,
                process_total,
                process_risk,
                min(assessment.confidence + 2, 91),
                process_costs,
                [
                    ("ಸಂಸ್ಕರಣಾ ಖರೀದಿದಾರರು ತಾಜಾ ಮಾರುಕಟ್ಟೆ ಮೌಲ್ಯ ಕಡಿಮೆ ಮಾಡುವ ಮೇಲ್ಮೈ ದೋಷಗಳನ್ನು ಕೆಲವು ಮಟ್ಟಿಗೆ ಸ್ವೀಕರಿಸಬಹುದು." if is_kn else "Processing buyers can accept cosmetic defects that reduce fresh-market value."),
                    (f"ಅಂದಾಜು ಸಂಸ್ಕರಣಾ ಮೌಲ್ಯ ಪ್ರತಿ ಕ್ವಿಂಟಲ್‌ಗೆ ₹{process_price:,.0f}." if is_kn else f"Estimated processor realization is ₹{process_price:,.0f} per quintal."),
                    ("ಈ ಆಯ್ಕೆ ತಾಜಾ ಮಾರುಕಟ್ಟೆಯ ತಿರಸ್ಕಾರ ಅಪಾಯವನ್ನು ಕಡಿಮೆ ಮಾಡಿ ವಾಣಿಜ್ಯ ಬಳಕೆಯನ್ನು ಉಳಿಸುತ್ತದೆ." if is_kn else "The option limits fresh-market rejection exposure while preserving commercial utilization."),
                ],
            )
        )

        # WAIT / DELAYED RELEASE
        wait_days = min(7, max(3, storage_days // 2))
        wait_index = min(wait_days - 1, len(forecast) - 1) if forecast else 0
        wait_base = forecast[wait_index]["predicted_price"] if forecast else base_modal * 1.015
        wait_price = wait_base * grade_factor
        wait_risk = self._clamp(
            18
            + assessment.surface_defect_severity * 0.27
            + assessment.rejection_probability * 0.25
            + wait_days * 0.8
        )
        wait_acceptance = max(0.42, acceptance - wait_risk / 100 * 0.13)
        wait_gross = wait_price * quintals * wait_acceptance
        wait_costs = {
            "transport": transport,
            "handling": handling,
            "storage": options.storage_cost_per_quintal_day * quintals * wait_days * 0.45,
            "processing": 0.0,
            "expected_loss": wait_gross * wait_risk / 100 * 0.16,
        }
        wait_total = sum(wait_costs.values())
        wait_net = wait_gross - wait_total
        candidates.append(
            self._candidate(
                "WAIT",
                "ಮಾರುಕಟ್ಟೆ ಬಿಡುಗಡೆ ತಡಮಾಡಿ" if is_kn else "Delay market release",
                best_market_name,
                (f"{wait_days} ದಿನಗಳ ನಂತರ ಮಾರುಕಟ್ಟೆ ಮರುಪರಿಶೀಲಿಸಿ" if is_kn else f"Review market in {wait_days} days"),
                wait_price,
                wait_gross,
                wait_net,
                wait_total,
                wait_risk,
                min(assessment.confidence, 74.0),
                wait_costs,
                [
                    (f"ಸಮೀಪಕಾಲದ ಅಂದಾಜಿನಲ್ಲಿ ಪ್ರತಿ ಕ್ವಿಂಟಲ್‌ಗೆ ಸುಮಾರು ₹{wait_base:,.0f} ಮಾದರಿ ಬೆಲೆ ಸಾಧ್ಯತೆ ಇದೆ." if is_kn else f"Near-term forecast indicates a possible modal price near ₹{wait_base:,.0f} per quintal."),
                    ("ಲಾಟ್ ಅನ್ನು ತಂಪಾಗಿ, ಒಣವಾಗಿ ಮತ್ತು ಗಾಳಿಯಾಡುವಂತೆ ಇಡಲು ಸಾಧ್ಯವಾದಾಗ ಮಾತ್ರ ತಡಮಾಡುವುದು ಸೂಕ್ತ." if is_kn else "Delay is only suitable when the batch can be kept cool, dry and ventilated."),
                    (f"ಅಂದಾಜು ಹಿಡುವಳಿ ಅಪಾಯ {wait_risk:.1f}/100." if is_kn else f"The estimated holding risk is {wait_risk:.1f}/100."),
                ],
            )
        )

        # Quality-linked commercial constraints from the report's decision matrix.
        for c in candidates:
            if assessment.quality_grade == "D" and c.action in {"STORE", "WAIT"}:
                c.score -= abs(c.net_profit) * 0.30 + 1800
                c.reasons.append("ಕಡಿಮೆ ಗ್ರೇಡ್ ಲಾಟ್‌ನಲ್ಲಿ ಗುಣಮಟ್ಟ ಕುಸಿತದ ಅಪಾಯ ಹೆಚ್ಚು ಇರುವುದರಿಂದ ಸಂಗ್ರಹಣೆ ಕಡಿಮೆ ಅಂಕ ಪಡೆಯುತ್ತದೆ." if is_kn else "Low-grade storage is penalized because deterioration risk is high.")
            if assessment.quality_grade == "C" and c.action == "PROCESS":
                c.score += 650
                c.reasons.append("ವರದಿ ನಿರ್ಧಾರ ಮ್ಯಾಟ್ರಿಕ್ಸ್‌ನಲ್ಲಿ ಗ್ರೇಡ್ C ಸಂಸ್ಕರಣಾ ಬಳಕೆಗೆ ಹೊಂದಿಕೊಳ್ಳುತ್ತದೆ." if is_kn else "Grade C aligns with stable processor utilization in the report decision matrix.")
            if assessment.quality_grade == "A" and c.action == "SELL_NOW":
                c.score += 900
                c.reasons.append("ಉತ್ತಮ ತಾಜಾ ಮಾರುಕಟ್ಟೆಯಲ್ಲಿ ಪ್ರೀಮಿಯಂ ಗುಣಮಟ್ಟಕ್ಕೆ ಹೆಚ್ಚಿನ ಮೌಲ್ಯ ದೊರೆಯುತ್ತದೆ." if is_kn else "Premium quality is rewarded in a strong fresh market.")
            if assessment.sprout_severity > 28 and c.action in {"STORE", "WAIT"}:
                c.score -= 1200
                c.reasons.append("ಮೊಳಕೆ ಸೂಚನೆಗಳು ತಡವಾದ ಮಾರಾಟವನ್ನು ಕಡಿಮೆ ಸೂಕ್ತವಾಗಿಸುತ್ತವೆ." if is_kn else "Sprout indicators make delayed sale less suitable.")

        ranked = sorted(candidates, key=lambda c: c.score, reverse=True)
        winner = ranked[0]
        margin = winner.score - ranked[1].score if len(ranked) > 1 else 0
        confidence = self._clamp(58 + min(abs(margin) / 120, 22) + assessment.confidence * 0.16, 55, 94)

        # Exact, auditable contribution decomposition for the selected pathway.
        # For the deterministic engine these are preferable to approximate SHAP values;
        # the ML folder also contains SHAP tooling for a learned recommendation model.
        benchmark_profit = float(sum(c.net_profit for c in ranked) / len(ranked))
        decision_factors = [
            {
                "factor": "Expected operating profit",
                "value": round(winner.net_profit, 2),
                "contribution": round(winner.net_profit - benchmark_profit, 2),
                "direction": "positive" if winner.net_profit >= benchmark_profit else "negative",
                "explanation": "Difference between this pathway and the average net profit of all evaluated pathways.",
            },
            {
                "factor": "Quality grade adjustment",
                "value": assessment.quality_grade,
                "contribution": round((grade_factor - 1.0) * base_modal * quintals, 2),
                "direction": "positive" if grade_factor >= 1.0 else "negative",
                "explanation": f"Grade {assessment.quality_grade} changes the market price factor to {grade_factor:.2f}.",
            },
            {
                "factor": "Rejection exposure",
                "value": round(assessment.rejection_probability, 2),
                "contribution": round(-winner.gross_revenue * assessment.rejection_probability / 100 * 0.10, 2),
                "direction": "negative",
                "explanation": "Higher visual rejection probability reduces expected sale realization.",
            },
            {
                "factor": "Risk penalty",
                "value": round(winner.risk_score, 2),
                "contribution": round(-(max(0.0, winner.net_profit) * winner.risk_score / 100 * 0.34 + winner.risk_score * 12), 2),
                "direction": "negative",
                "explanation": "Commercial uncertainty, deterioration and pathway-specific failure risk are penalized.",
            },
            {
                "factor": "Market price signal",
                "value": round(base_modal, 2),
                "contribution": round((base_modal - 2000.0) * quintals * 0.25, 2),
                "direction": "positive" if base_modal >= 2000 else "negative",
                "explanation": "Contribution relative to the conservative ₹2,000/q reference price.",
            },
        ]

        explanation = list(winner.reasons)
        explanation.extend(
            [
                (f"{len(ranked)} ಮಾರ್ಗಗಳಲ್ಲಿ ಆಯ್ದ ಆಯ್ಕೆಗೆ ಅತ್ಯಧಿಕ ಅಪಾಯ-ಹೊಂದಿಸಿದ ಆರ್ಥಿಕ ಅಂಕ ಬಂದಿದೆ." if is_kn else f"The selected option has the highest risk-adjusted economic score among {len(ranked)} pathways."),
                (f"ನಿರೀಕ್ಷಿತ ಕೊಯ್ಲಿನ ನಂತರದ ಕಾರ್ಯಾಚರಣಾ ಲಾಭ ₹{winner.net_profit:,.0f}; ಈಗಾಗಲೇ ಖರ್ಚಾದ ಬೆಳೆ ವೆಚ್ಚ ಇದರಲ್ಲಿ ಸೇರಿಲ್ಲ." if is_kn else f"Expected post-harvest operating profit is ₹{winner.net_profit:,.0f}; this excludes cultivation cost already incurred."),
                (f"ಚಿತ್ರ ಗುಣಮಟ್ಟ ಅಂಕ {assessment.quality_score:.1f}/100 ಮತ್ತು ತಿರಸ್ಕಾರ ಸಾಧ್ಯತೆ {assessment.rejection_probability:.1f}% ಅನ್ನು ಲೆಕ್ಕದಲ್ಲಿ ಸೇರಿಸಲಾಗಿದೆ." if is_kn else f"Image quality score {assessment.quality_score:.1f}/100 and rejection probability {assessment.rejection_probability:.1f}% were included."),
            ]
        )

        if is_kn:
            factor_map = {
                "Expected operating profit": ("ನಿರೀಕ್ಷಿತ ಕಾರ್ಯಾಚರಣಾ ಲಾಭ", "ಈ ಮಾರ್ಗದ ಲಾಭ ಮತ್ತು ಎಲ್ಲಾ ಮಾರ್ಗಗಳ ಸರಾಸರಿ ಲಾಭದ ನಡುವಿನ ವ್ಯತ್ಯಾಸ."),
                "Quality grade adjustment": ("ಗುಣಮಟ್ಟ ಗ್ರೇಡ್ ಹೊಂದಾಣಿಕೆ", f"ಗ್ರೇಡ್ {assessment.quality_grade} ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ಗುಣಕವನ್ನು {grade_factor:.2f} ಗೆ ಬದಲಿಸುತ್ತದೆ."),
                "Rejection exposure": ("ತಿರಸ್ಕಾರ ಅಪಾಯ", "ಹೆಚ್ಚಿನ ದೃಶ್ಯ ತಿರಸ್ಕಾರ ಸಾಧ್ಯತೆ ನಿರೀಕ್ಷಿತ ಮಾರಾಟ ಮೌಲ್ಯವನ್ನು ಕಡಿಮೆ ಮಾಡುತ್ತದೆ."),
                "Risk penalty": ("ಅಪಾಯ ಕಡಿತ", "ವಾಣಿಜ್ಯ ಅನಿಶ್ಚಿತತೆ, ಗುಣಮಟ್ಟ ಕುಸಿತ ಮತ್ತು ಮಾರ್ಗ ವಿಫಲತೆಯ ಅಪಾಯಕ್ಕೆ ಕಡಿತ ಅನ್ವಯಿಸಲಾಗಿದೆ."),
                "Market price signal": ("ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ಸೂಚನೆ", "ಸಂರಕ್ಷಣಾತ್ಮಕ ₹2,000/ಕ್ವಿಂಟಲ್ ಉಲ್ಲೇಖ ಬೆಲೆಯೊಂದಿಗೆ ಹೋಲಿಸಿದ ಕೊಡುಗೆ."),
            }
            for item in decision_factors:
                if item["factor"] in factor_map:
                    item["factor"], item["explanation"] = factor_map[item["factor"]]

        return {
            "recommended_action": winner.action,
            "recommended_market": winner.market,
            "recommended_timing": winner.timing,
            "expected_selling_price": round(winner.selling_price, 2),
            "expected_gross_revenue": round(winner.gross_revenue, 2),
            "expected_net_profit": round(winner.net_profit, 2),
            "expected_roi": round(winner.roi, 2),
            "risk_score": round(winner.risk_score, 2),
            "confidence": round(confidence, 2),
            "alternatives": [c.public() for c in ranked],
            "explanation": explanation,
            "cost_breakdown": {k: round(v, 2) for k, v in winner.costs.items()},
            "decision_factors": decision_factors,
        }

    def _candidate(
        self,
        action: str,
        title: str,
        market: str,
        timing: str,
        selling_price: float,
        gross: float,
        net: float,
        total_cost: float,
        risk: float,
        confidence: float,
        costs: dict[str, float],
        reasons: list[str],
    ) -> Candidate:
        roi = net / max(total_cost, 1.0) * 100
        risk_penalty = max(0.0, net) * risk / 100 * 0.34 + risk * 12
        score = net - risk_penalty
        return Candidate(
            action=action,
            title=title,
            market=market,
            timing=timing,
            selling_price=round(selling_price, 2),
            gross_revenue=round(gross, 2),
            net_profit=round(net, 2),
            roi=round(roi, 2),
            risk_score=round(risk, 2),
            confidence=round(confidence, 2),
            score=round(score, 2),
            costs={k: round(v, 2) for k, v in costs.items()},
            reasons=reasons,
        )
