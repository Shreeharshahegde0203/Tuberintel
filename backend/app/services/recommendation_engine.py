from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import median
from typing import Any

from app.models import Batch, MarketPrice, QualityAssessment
from app.schemas.batches import AnalysisOptions
from app.services.quality_valuation import apply_valuation


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
    eligible: bool
    assumption_status: str
    price_source: str

    def public(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("score", None)
        return data


class RecommendationEngine:
    """Transparent post-harvest economics.

    Financial values are derived only from explicit prices, quantity and explicit
    post-harvest costs/loss assumptions. Vision outputs are kept as risk/context;
    quality adjustment is applied separately with explicit, auditable assumptions.
    """

    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
        return max(low, min(high, value))

    @staticmethod
    def _clean(value: str | None) -> str:
        return (value or "").strip().casefold()

    def _market_reference(
        self,
        batch: Batch,
        latest_markets: list[MarketPrice],
    ) -> tuple[float, str, str, bool]:
        rows = [row for row in latest_markets if float(getattr(row, "modal_price", 0) or 0) > 0]
        if not rows:
            return 0.0, batch.intended_market or "Market unavailable", "No current market observation", False

        intended = self._clean(batch.intended_market)
        selected_rows = [row for row in rows if self._clean(getattr(row, "market", None)) == intended] if intended else []
        reference_rows = selected_rows or rows

        variety = self._clean(getattr(batch, "variety", None))
        if variety and variety not in {"unspecified", "not specified", "local"}:
            variety_rows = [row for row in reference_rows if self._clean(getattr(row, "variety", None)) == variety]
            if variety_rows:
                reference_rows = variety_rows

        modal = float(median(float(row.modal_price) for row in reference_rows))
        first = reference_rows[0]
        market_name = str(getattr(first, "market", None) or batch.intended_market or "Market")
        source = str(getattr(first, "source", None) or "AGMARKNET / market observation")
        date_value = getattr(first, "arrival_date", None)
        source_text = f"{source} modal price" + (f" · {date_value}" if date_value else "")
        return modal, market_name, source_text, True

    # TUBERINTEL QUALITY VALUE V1
    def evaluate(self, batch, assessment, latest_markets, forecast, options):
        result = self._evaluate_reference(batch, assessment, latest_markets, forecast, options)
        return apply_valuation(result, assessment, batch, options)

    def _evaluate_reference(
        self,
        batch: Batch,
        assessment: QualityAssessment,
        latest_markets: list[MarketPrice],
        forecast: list[dict[str, Any]],
        options: AnalysisOptions,
    ) -> dict[str, Any]:
        is_kn = options.language == "kn"
        quintals = float(batch.quantity_kg) / 100.0
        tonnes = float(batch.quantity_kg) / 1000.0
        base_modal, market_name, market_source, market_available = self._market_reference(batch, latest_markets)

        transport = float(options.distance_km) * tonnes * float(options.transport_cost_per_km_tonne)
        handling = quintals * float(options.handling_cost_per_quintal)
        storage_loss = getattr(options, "expected_storage_loss_percent", None)
        if storage_loss is not None:
            storage_loss = self._clamp(float(storage_loss), 0.0, 100.0)

        candidates: list[Candidate] = []

        # SELL NOW: AGMARKNET/market modal price is a wholesale reference. Do not
        # invent a grade multiplier or convert visual rejection risk into rupees.
        sell_gross = base_modal * quintals if market_available else 0.0
        sell_costs = {
            "transport": transport if market_available else 0.0,
            "handling": handling if market_available else 0.0,
            "storage": 0.0,
            "processing": 0.0,
            "expected_loss": 0.0,
        }
        sell_net = sell_gross - sum(sell_costs.values())
        sell_risk = self._clamp(
            float(assessment.rejection_probability) * 0.60
            + float(assessment.surface_defect_severity) * 0.40
        )
        candidates.append(
            self._candidate(
                action="SELL_NOW",
                title="ಈಗಲೇ ಮಾರಾಟ ಮಾಡಿ" if is_kn else "Sell now",
                market=market_name,
                timing="24–48 ಗಂಟೆಗಳೊಳಗೆ" if is_kn else "Within 24–48 hours",
                selling_price=base_modal,
                gross=sell_gross,
                net=sell_net,
                risk=sell_risk,
                confidence=float(assessment.confidence),
                costs=sell_costs,
                reasons=[
                    (
                        f"{batch.quantity_kg:,.0f} kg = {quintals:,.2f} ಕ್ವಿಂಟಲ್; ಉಲ್ಲೇಖ ಒಟ್ಟು ಮೌಲ್ಯ = {quintals:,.2f} × ₹{base_modal:,.0f} = ₹{sell_gross:,.0f}."
                        if is_kn
                        else f"{batch.quantity_kg:,.0f} kg = {quintals:,.2f} quintals; reference gross value = {quintals:,.2f} × ₹{base_modal:,.0f}/qtl = ₹{sell_gross:,.0f}."
                    ),
                    (
                        "ಚಿತ್ರ ಗ್ರೇಡ್ ಅಥವಾ ತಿರಸ್ಕಾರ ಅಂಕದಿಂದ ಯಾವುದೇ ಸ್ವಯಂಚಾಲಿತ ರೂಪಿ ಕಡಿತ ಅನ್ವಯಿಸಲಾಗಿಲ್ಲ; ನಿಜವಾದ ಖರೀದಿದಾರರ ಕಡಿತ ವೇಳಾಪಟ್ಟಿ ಇಲ್ಲದೆ ಅದನ್ನು ಊಹಿಸಲಾಗುವುದಿಲ್ಲ."
                        if is_kn
                        else "No automatic rupee discount is applied from the vision grade or rejection score; a buyer-specific deduction schedule is required for that."
                    ),
                    (
                        "ಮಂಡಿ modal ಬೆಲೆ ಒಂದು wholesale reference; ನಿಜವಾದ ಲಾಟ್ ಬೆಲೆ ಮಾತುಕತೆ, variety, grade ಮತ್ತು buyer inspection ಆಧರಿಸಿ ಬದಲಾಗಬಹುದು."
                        if is_kn
                        else "The mandi modal price is a wholesale reference; the actual lot price can differ after negotiation, variety/grade checks and buyer inspection."
                    ),
                ],
                eligible=market_available,
                assumption_status="Current market price available" if market_available else "Current market price required",
                price_source=market_source,
            )
        )

        # STORE: use the selected-market forecast and a USER-SUPPLIED expected
        # marketable weight loss. Without that assumption the route is shown but
        # is not allowed to win the ranking.
        storage_days = int(options.storage_days)
        forecast_prices = {point.get("horizon_days", index): float(point["predicted_price"]) for index, point in enumerate(forecast, 1)}
        future_base = forecast_prices.get(storage_days, 0.0)
        store_gross = future_base * quintals if market_available else 0.0
        storage_cost = float(options.storage_cost_per_quintal_day) * quintals * storage_days
        store_loss_value = store_gross * (storage_loss or 0.0) / 100.0
        store_costs = {
            "transport": transport if market_available else 0.0,
            "handling": handling if market_available else 0.0,
            "storage": storage_cost if market_available else 0.0,
            "processing": 0.0,
            "expected_loss": store_loss_value,
        }
        store_net = store_gross - sum(store_costs.values())
        storage_risk = self._clamp(
            12
            + float(assessment.sprout_severity) * 0.30
            + float(assessment.bruise_severity) * 0.18
            + float(assessment.scab_severity) * 0.12
            + float(assessment.discoloration_severity) * 0.12
            + storage_days * 0.45
        )
        store_eligible = market_available and future_base > 0 and storage_loss is not None
        candidates.append(
            self._candidate(
                action="STORE",
                title="ಸಂಗ್ರಹಿಸಿ ನಂತರ ಮಾರಾಟ ಮಾಡಿ" if is_kn else "Store and sell later",
                market=market_name,
                timing=f"ಸುಮಾರು {storage_days} ದಿನಗಳ ನಂತರ" if is_kn else f"After approximately {storage_days} days",
                selling_price=future_base,
                gross=store_gross,
                net=store_net,
                risk=storage_risk,
                confidence=min(float(assessment.confidence), 78.0),
                costs=store_costs,
                reasons=[
                    (
                        f"{storage_days}-ದಿನಗಳ forecast reference ₹{future_base:,.0f}/ಕ್ವಿಂಟಲ್."
                        if is_kn
                        else f"The {storage_days}-day selected-market forecast reference is ₹{future_base:,.0f}/qtl."
                    ),
                    (
                        f"ಬಳಕೆದಾರ ನೀಡಿದ ಸಂಗ್ರಹ ನಷ್ಟ {storage_loss:.1f}% ಅನ್ನು ₹{store_loss_value:,.0f} physical-loss value ಆಗಿ ಲೆಕ್ಕಿಸಲಾಗಿದೆ."
                        if is_kn and storage_loss is not None
                        else f"User-supplied storage loss of {storage_loss:.1f}% is valued at ₹{store_loss_value:,.0f}."
                        if storage_loss is not None
                        else "Storage/Wait is not ranked until you provide expected marketable weight loss (%) for the selected storage horizon."
                    ),
                    (
                        "Vision storage risk is advisory only; it is not silently converted into kilograms or rupees."
                        if not is_kn
                        else "Vision storage risk ಸಲಹೆಗಾಗಿ ಮಾತ್ರ; ಅದನ್ನು ಗುಪ್ತವಾಗಿ kg ಅಥವಾ ರೂಪಾಯಿಗೆ ಪರಿವರ್ತಿಸಲಾಗುವುದಿಲ್ಲ."
                    ),
                ],
                eligible=store_eligible,
                assumption_status="Forecast and storage loss supplied" if store_eligible else "Matching forecast and storage loss % required",
                price_source="Selected-market forecast" if future_base else "Forecast unavailable",
            )
        )

        # PROCESS means SALE OF RAW POTATOES TO A PROCESSOR, not farmer-side
        # value addition. Therefore it must use an explicit processor quote.
        processor_quote = options.processor_price_per_quintal
        process_eligible = processor_quote is not None and float(processor_quote) > 0
        process_price = float(processor_quote) if process_eligible else 0.0
        process_gross = process_price * quintals if process_eligible else 0.0
        process_costs = {
            "transport": transport if process_eligible else 0.0,
            "handling": handling if process_eligible else 0.0,
            "storage": 0.0,
            "processing": 0.0,
            "expected_loss": 0.0,
        }
        process_net = process_gross - sum(process_costs.values())
        process_risk = self._clamp(
            22
            + float(assessment.discoloration_severity) * 0.18
            + float(assessment.sprout_severity) * 0.16
            + float(assessment.rejection_probability) * 0.18
        )
        candidates.append(
            self._candidate(
                action="PROCESS",
                title="ಸಂಸ್ಕರಣಾ ಖರೀದಿದಾರರಿಗೆ ಮಾರಾಟ" if is_kn else "Sell to a processor",
                market="Processor / contract buyer",
                timing="Quote/contract ಪ್ರಕಾರ" if is_kn else "According to buyer quote / contract",
                selling_price=process_price,
                gross=process_gross,
                net=process_net,
                risk=process_risk,
                confidence=min(float(assessment.confidence), 80.0) if process_eligible else 0.0,
                costs=process_costs,
                reasons=[
                    (
                        f"Processor quote ₹{process_price:,.0f}/ಕ್ವಿಂಟಲ್ ಅನ್ನು ನೇರವಾಗಿ {quintals:,.2f} ಕ್ವಿಂಟಲ್‌ಗೆ ಅನ್ವಯಿಸಲಾಗಿದೆ."
                        if is_kn and process_eligible
                        else f"The entered processor quote of ₹{process_price:,.0f}/qtl is applied directly to {quintals:,.2f} quintals."
                        if process_eligible
                        else "PROCESS is not ranked because no processor quote was supplied. TuberIntel does not invent a processor price."
                    ),
                    (
                        "This route means selling raw potatoes to a processor; it does not assume that the farmer earns the value of chips/fries/starch."
                        if not is_kn
                        else "ಈ ಮಾರ್ಗವು ಕಚ್ಚಾ ಆಲೂಗಡ್ಡೆಯನ್ನು processor ಗೆ ಮಾರಾಟ ಮಾಡುವುದಾಗಿದೆ; chips/fries/starch ಮೌಲ್ಯವನ್ನು ರೈತರಿಗೆ ಸೇರಿಸಲಾಗುವುದಿಲ್ಲ."
                    ),
                    (
                        "Processor acceptance can depend on variety, dry matter, reducing sugars and contract specifications that image inspection alone cannot verify."
                        if not is_kn
                        else "Processor acceptance variety, dry matter, reducing sugars ಮತ್ತು contract specifications ಮೇಲೆ ಅವಲಂಬಿಸಬಹುದು; ಚಿತ್ರ ಪರಿಶೀಲನೆ ಮಾತ್ರ ಇದನ್ನು ದೃಢಪಡಿಸಲಾರದು."
                    ),
                ],
                eligible=process_eligible,
                assumption_status="Processor quote supplied" if process_eligible else "Processor quote required to rank PROCESS",
                price_source="User-entered processor quote" if process_eligible else "No processor quote",
            )
        )

        # WAIT: short holding scenario. Apply the same explicit storage-loss
        # assumption proportionally to the shorter holding period.
        wait_days = min(7, max(1, storage_days // 2 if storage_days else 3))
        wait_price = forecast_prices.get(wait_days, 0.0)
        wait_gross = wait_price * quintals if market_available else 0.0
        if storage_loss is not None and storage_days > 0:
            wait_loss_pct = storage_loss * wait_days / storage_days
        else:
            wait_loss_pct = storage_loss or 0.0
        wait_loss_value = wait_gross * wait_loss_pct / 100.0
        wait_storage_cost = float(options.storage_cost_per_quintal_day) * quintals * wait_days
        wait_costs = {
            "transport": transport if market_available else 0.0,
            "handling": handling if market_available else 0.0,
            "storage": wait_storage_cost if market_available else 0.0,
            "processing": 0.0,
            "expected_loss": wait_loss_value,
        }
        wait_net = wait_gross - sum(wait_costs.values())
        wait_risk = self._clamp(
            15
            + float(assessment.surface_defect_severity) * 0.20
            + float(assessment.rejection_probability) * 0.20
            + wait_days * 0.55
        )
        wait_eligible = market_available and wait_price > 0 and storage_loss is not None
        candidates.append(
            self._candidate(
                action="WAIT",
                title="ಮಾರುಕಟ್ಟೆ ಬಿಡುಗಡೆ ತಡಮಾಡಿ" if is_kn else "Delay market release",
                market=market_name,
                timing=f"{wait_days} ದಿನಗಳಲ್ಲಿ ಮರುಪರಿಶೀಲಿಸಿ" if is_kn else f"Review market in {wait_days} days",
                selling_price=wait_price,
                gross=wait_gross,
                net=wait_net,
                risk=wait_risk,
                confidence=min(float(assessment.confidence), 74.0),
                costs=wait_costs,
                reasons=[
                    (
                        f"{wait_days}-ದಿನಗಳ forecast reference ₹{wait_price:,.0f}/ಕ್ವಿಂಟಲ್."
                        if is_kn
                        else f"The {wait_days}-day selected-market forecast reference is ₹{wait_price:,.0f}/qtl."
                    ),
                    (
                        f"Short-hold loss uses {wait_loss_pct:.2f}% by prorating the user-supplied {storage_loss:.2f}% loss assumption over {storage_days} days."
                        if storage_loss is not None and storage_days > 0 and not is_kn
                        else "WAIT is not ranked until an expected storage/holding loss (%) is supplied."
                        if storage_loss is None and not is_kn
                        else f"ಬಳಕೆದಾರರ loss assumption ಆಧರಿಸಿ short-hold loss {wait_loss_pct:.2f}% ಬಳಸಲಾಗಿದೆ."
                    ),
                ],
                eligible=wait_eligible,
                assumption_status="Forecast and holding loss supplied" if wait_eligible else "Matching forecast and storage loss % required",
                price_source="Selected-market forecast" if wait_price else "Forecast unavailable",
            )
        )

        eligible = [candidate for candidate in candidates if candidate.eligible]
        if eligible:
            eligible_sorted = sorted(eligible, key=lambda c: (c.net_profit, -c.risk_score), reverse=True)
            winner = eligible_sorted[0]
        else:
            # Keep the response contract stable, but make the lack of usable
            # commercial evidence explicit rather than fabricating a price.
            winner = candidates[0]

        ranked = sorted(
            candidates,
            key=lambda c: (1 if c.eligible else 0, c.net_profit if c.eligible else -1e18, -c.risk_score),
            reverse=True,
        )

        data_completeness = 35.0 if market_available else 0.0
        if winner.action in {"STORE", "WAIT"} and storage_loss is not None:
            data_completeness += 15.0
        elif winner.action == "PROCESS" and process_eligible:
            data_completeness += 15.0
        else:
            data_completeness += 10.0
        confidence = self._clamp(float(assessment.confidence) * 0.45 + data_completeness, 0, 90)

        decision_factors = [
            {
                "factor": "Reference gross value",
                "value": round(winner.gross_revenue, 2),
                "contribution": round(winner.gross_revenue, 2),
                "direction": "positive",
                "explanation": f"{quintals:.2f} quintals × ₹{winner.selling_price:,.2f}/qtl.",
            }
        ]
        factor_names = {
            "transport": "Transport cost",
            "handling": "Handling cost",
            "storage": "Storage/holding cost",
            "processing": "Processing cost",
            "expected_loss": "User-assumed physical loss value",
        }
        for key, amount in winner.costs.items():
            if amount <= 0:
                continue
            decision_factors.append(
                {
                    "factor": factor_names.get(key, key.replace("_", " ").title()),
                    "value": round(amount, 2),
                    "contribution": round(-amount, 2),
                    "direction": "negative",
                    "explanation": "Explicit post-harvest cost/assumption used in the arithmetic.",
                }
            )

        explanation = list(winner.reasons)
        explanation.extend(
            [
                (
                    f"ಕೊಯ್ಲಿನ ನಂತರದ ನಿವ್ವಳ ಸಾಕಾರ ಮೌಲ್ಯ ₹{winner.net_profit:,.0f}; ಇದು reference gross value ನಿಂದ explicit post-harvest costs ಅನ್ನು ಕಡಿತ ಮಾಡಿದ ಮೌಲ್ಯ."
                    if is_kn
                    else f"Post-harvest net realization is ₹{winner.net_profit:,.0f}: reference/quoted gross value minus explicit post-harvest costs."
                ),
                (
                    "ಬೆಳೆ ಬೆಳೆಸುವ ಈಗಾಗಲೇ ಉಂಟಾದ ವೆಚ್ಚ ಇದರಲ್ಲಿ ಸೇರಿಲ್ಲ; ಆದ್ದರಿಂದ ಇದನ್ನು ಸಂಪೂರ್ಣ farm profit ಎಂದು ಓದಬಾರದು."
                    if is_kn
                    else "Cultivation cost already incurred is excluded, so this must not be read as total farm profit."
                ),
                (
                    f"Vision grade {assessment.quality_grade} and rejection score {assessment.rejection_probability:.1f}% are shown as commercial-risk evidence, not as an invented automatic price haircut."
                    if not is_kn
                    else f"Vision grade {assessment.quality_grade} ಮತ್ತು rejection score {assessment.rejection_probability:.1f}% commercial-risk evidence ಆಗಿವೆ; ಅವುಗಳನ್ನು ಸ್ವಯಂಚಾಲಿತ ಬೆಲೆ ಕಡಿತವಾಗಿ ಬಳಸಲಾಗಿಲ್ಲ."
                ),
            ]
        )

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
            "alternatives": [candidate.public() for candidate in ranked],
            "explanation": explanation,
            "cost_breakdown": {key: round(value, 2) for key, value in winner.costs.items()},
            "decision_factors": decision_factors,
        }

    def _candidate(
        self,
        *,
        action: str,
        title: str,
        market: str,
        timing: str,
        selling_price: float,
        gross: float,
        net: float,
        risk: float,
        confidence: float,
        costs: dict[str, float],
        reasons: list[str],
        eligible: bool,
        assumption_status: str,
        price_source: str,
    ) -> Candidate:
        # Keep the API field name `roi` for backward compatibility, but the value
        # is now a bounded net-realization margin (net / gross), not the old
        # misleading net / post-harvest-cost ratio that could show 300%+.
        realization_margin = (net / gross * 100.0) if gross > 0 else 0.0
        return Candidate(
            action=action,
            title=title,
            market=market,
            timing=timing,
            selling_price=round(selling_price, 2),
            gross_revenue=round(gross, 2),
            net_profit=round(net, 2),
            roi=round(realization_margin, 2),
            risk_score=round(risk, 2),
            confidence=round(confidence, 2),
            score=round(net, 2) if eligible else -1e18,
            costs={key: round(value, 2) for key, value in costs.items()},
            reasons=reasons,
            eligible=eligible,
            assumption_status=assumption_status,
            price_source=price_source,
        )
