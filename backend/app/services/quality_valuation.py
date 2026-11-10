"""Transparent prototype valuation; coefficients require local buyer calibration."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

DEFAULT_POLICY = {
    "version": "quality-value-v1",
    "calibration_status": "uncalibrated_scenario",
    "reference_quality_score": 88.0,
    "discount_exponent": 1.5,
    "note": "Prototype curve, not an official grade-to-price schedule. Calibrate using paired batch inspections and actual buyer prices.",
}


def number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def fraction(value: Any, default: float = 1.0) -> float:
    result = number(value)
    return default if result is None else max(0.0, min(1.0, result / 100.0))


def load_policy() -> dict[str, Any]:
    path = Path(__file__).with_name("quality_value_policy.json")
    policy = {**DEFAULT_POLICY, **(json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {})}
    reference = number(policy.get("reference_quality_score"))
    exponent = number(policy.get("discount_exponent"))
    if reference is None or not 0 < reference <= 100 or exponent is None or not 0 < exponent <= 10:
        raise ValueError("Invalid quality_value_policy: reference score must be (0,100], exponent (0,10].")
    # A config flag cannot turn prototype coefficients into validated estimates.
    policy["calibration_status"] = "uncalibrated_scenario"
    return policy


def score_factor(score: float, policy: dict[str, Any]) -> float:
    return min(1.0, max(0.0, score) / float(policy["reference_quality_score"])) ** float(policy["discount_exponent"])


def _fusion(record: dict[str, Any]) -> dict[str, Any]:
    # Known per-image quality_score is already fused in current image analysis.
    for key in ("vision_fusion", "fusion", "fusion_result"):
        data = record.get(key)
        if isinstance(data, dict) and number(data.get("quality_score")) is not None:
            return data
    return record


def sample_records(assessment: Any) -> tuple[list[tuple[dict[str, Any], float]], str]:
    summary = getattr(assessment, "feature_summary", None) or {}
    images = summary.get("per_image") if isinstance(summary, dict) else None
    records: list[tuple[dict[str, Any], float]] = []
    region_count = 0
    image_count = 0
    for image in images or []:
        if not isinstance(image, dict):
            continue
        # Never infer individual quality from a classifier probability or ROI size.
        predictions = image.get("trained_predictions") or (image.get("features") or {}).get("trained_predictions") or {}
        region_list = predictions.get("regions") if isinstance(predictions, dict) else None
        if isinstance(region_list, list) and region_list and all(
            isinstance(row, dict) and number(_fusion(row).get("quality_score")) is not None for row in region_list
        ):
            records.extend((_fusion(row), 1.0) for row in region_list)
            region_count += len(region_list)
        else:
            data = _fusion(image)
            if number(data.get("quality_score")) is not None:
                count = number(image.get("potato_count"))
                # Count-weighted quality index is a sampling assumption, NOT kg.
                records.append((data, max(1.0, count or 1.0)))
                image_count += 1
    if records:
        basis = "individual fused scores" if not image_count else "image fused scores weighted by detected count" if not region_count else "mixed individual/image fused scores"
        return records, basis
    score = number(getattr(assessment, "quality_score", None))
    return ([({"quality_score": score}, 1.0)] if score is not None else []), "aggregate fused score fallback"


def valuation(assessment: Any, options: Any) -> dict[str, Any]:
    policy = load_policy()
    mode = getattr(options, "quality_pricing_mode", "estimated")
    quote = number(getattr(options, "fresh_buyer_price_per_quintal", None))
    discount = number(getattr(options, "buyer_quality_discount_percent", None))
    accepted = number(getattr(options, "saleable_weight_percent", None))
    weight_factor = fraction(accepted)
    records, basis = sample_records(assessment)
    total = sum(weight for _, weight in records)
    estimated = sum(score_factor(float(row["quality_score"]), policy) * weight for row, weight in records) / total if total else None
    manual = quote is not None or discount is not None or accepted is not None
    if mode == "reference":
        price_factor, status, usable = 1.0, "Market reference only; quality adjustment disabled", True
    elif discount is not None:
        price_factor, status, usable = 1 - fraction(discount, 0.0), "User-supplied buyer discount", True
    elif mode == "manual":
        price_factor, status, usable = 1.0, "Buyer quote or discount required in manual mode", False
    else:
        price_factor, status, usable = estimated or 0.0, "Uncalibrated quality-adjusted scenario", estimated is not None
    return {
        "mode": mode, "status": status, "usable": usable,
        "reference_quality_score": policy["reference_quality_score"],
        "discount_exponent": policy["discount_exponent"],
        "price_factor": price_factor, "accepted_weight_factor": weight_factor,
        "factor": price_factor * weight_factor, "fresh_quote_per_quintal": quote,
        "sampling_basis": basis, "sample_record_count": len(records),
        "calibration_status": "user_supplied_terms" if manual and discount is not None else "reference_only" if mode == "reference" else "uncalibrated_scenario",
        "assumptions": [
            "Image quality score is an index, not a measured saleable mass fraction.",
            "Detected count weights assume a representative sample of similarly weighted potatoes; repeated views can bias this estimate.",
            "Market modal price is treated as the undiscounted reference; its actual grade composition may differ.",
            "No measured saleable-weight loss supplied; quantity retained at 100%." if accepted is None else f"User-supplied saleable-weight fraction: {accepted:.2f}%.",
            "Current quality factor held constant for future forecasts; future deterioration is not modelled by this curve.",
            policy["note"],
        ],
    }


def apply_valuation(result: dict[str, Any], assessment: Any, batch: Any, options: Any) -> dict[str, Any]:
    audit = valuation(assessment, options)
    quantity = float(batch.quantity_kg)
    quintals = quantity / 100.0
    candidates = result["alternatives"]
    for candidate in candidates:
        reference_price = float(candidate["selling_price"])
        factor = audit["factor"]
        reference_eligible = candidate.get("eligible", True)
        route_audit = dict(audit)
        if candidate["action"] == "PROCESS":
            # The processor's quality-specific quote already incorporates price terms.
            factor = audit["accepted_weight_factor"]
            usable = True
            route_audit.update(status="Processor quote supplied; no second quality discount", calibration_status="user_supplied_terms", usable=True)
        else:
            usable = audit["usable"]
            if candidate["action"] == "SELL_NOW" and audit["fresh_quote_per_quintal"] is not None:
                reference_price = audit["fresh_quote_per_quintal"]
                reference_eligible = True  # A quote does not require a live mandi row.
                factor, usable = audit["accepted_weight_factor"], True
                route_audit.update(status="Buyer quote supplied; verify scope and accepted weight", calibration_status="user_supplied_terms", usable=True)
        gross = reference_price * quintals * factor
        costs = dict(candidate["costs"])
        old_gross = float(candidate["gross_revenue"])
        # Storage loss is incremental to accepted weight, never applied twice.
        loss_fraction = float(costs.get("expected_loss", 0)) / old_gross if old_gross > 0 else 0.0
        costs["expected_loss"] = gross * loss_fraction
        if candidate["action"] == "SELL_NOW" and audit["fresh_quote_per_quintal"] is not None and not old_gross:
            costs["transport"] = float(options.distance_km) * (quantity / 1000) * float(options.transport_cost_per_km_tonne)
            costs["handling"] = quintals * float(options.handling_cost_per_quintal)
        net = gross - sum(costs.values())
        effective_price = reference_price * factor
        candidate.update({
            "selling_price": round(effective_price, 2),
            "gross_revenue": round(gross, 2), "net_profit": round(net, 2),
            "roi": round(net / gross * 100, 2) if gross else 0.0,
            "costs": {key: round(value, 2) for key, value in costs.items()},
            "eligible": bool(reference_eligible and usable and gross > 0),
            "assumption_status": route_audit["status"] if reference_eligible else candidate.get("assumption_status", "Input required"),
            "valuation": {**route_audit, "reference_price_per_quintal": round(reference_price, 2), "applied_factor": round(factor, 6), "effective_value_per_original_kg": round(effective_price / 100, 4)},
            "reasons": [
                f"{route_audit['status']}: effective value ₹{effective_price / 100:.2f}/original kg × {quantity:,.2f} kg = ₹{gross:,.2f} gross.",
                f"Reference/quoted rate ₹{reference_price / 100:.2f}/kg; applied value factor {factor:.4f}. " + ("Processor quote is not discounted again." if candidate["action"] == "PROCESS" else f"Basis: {audit['sampling_basis']}.") ,
                "Transport/handling/storage costs remain explicit; cultivation costs are excluded.",
            ],
        })
        if candidate["action"] == "SELL_NOW" and audit["fresh_quote_per_quintal"] is not None:
            candidate["price_source"] = "User-supplied fresh-buyer quote"
    candidates.sort(key=lambda c: (bool(c["eligible"]), c["net_profit"] if c["eligible"] else -1e18, -c["risk_score"]), reverse=True)
    eligible = [candidate for candidate in candidates if candidate["eligible"]]
    winner = eligible[0] if eligible else next(candidate for candidate in candidates if candidate["action"] == "SELL_NOW")
    result.update({
        "recommended_action": winner["action"], "recommended_market": winner["market"],
        "recommended_timing": winner["timing"] if eligible else "Buyer inspection / pricing inputs required",
        "expected_selling_price": winner["selling_price"], "expected_gross_revenue": winner["gross_revenue"],
        "expected_net_profit": winner["net_profit"], "expected_roi": winner["roi"],
        "risk_score": winner["risk_score"], "cost_breakdown": winner["costs"],
        "explanation": winner["reasons"] + audit["assumptions"] + ([] if eligible else ["No option is financially eligible; displayed values are scenarios, not an executable sale recommendation."]),
        "confidence": min(float(result["confidence"]), 50.0) if winner["valuation"]["calibration_status"] == "uncalibrated_scenario" else float(result["confidence"]),
    })
    # JSON fields retain provenance without database schema changes.
    summary = dict(getattr(assessment, "feature_summary", None) or {})
    summary["quality_valuation"] = winner["valuation"]
    assessment.feature_summary = summary
    factors = [{"factor": "Quality-adjusted gross value", "value": winner["gross_revenue"], "contribution": winner["gross_revenue"], "direction": "positive", "explanation": f"{quantity:.2f} kg × ₹{winner['selling_price'] / 100:.4f}/original kg. Includes adjustment once."}]
    for key, amount in winner["costs"].items():
        if amount:
            factors.append({"factor": key.replace("_", " ").title(), "value": amount, "contribution": -amount, "direction": "negative", "explanation": "Explicit post-harvest cost or incremental storage-loss assumption."})
    result["decision_factors"] = factors
    return result
