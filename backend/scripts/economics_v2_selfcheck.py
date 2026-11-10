from datetime import date
from types import SimpleNamespace as NS

from app.services.recommendation_engine import RecommendationEngine

batch = NS(
    quantity_kg=1000.0,
    intended_market="Test APMC",
    variety="Unspecified",
)

assessment = NS(
    quality_grade="D",
    rejection_probability=62.3,
    surface_defect_severity=58.4,
    confidence=83.6,
    sprout_severity=14.9,
    bruise_severity=93.1,
    scab_severity=100.0,
    discoloration_severity=31.4,
)

market = NS(
    modal_price=2000.0,
    market="Test APMC",
    source="AGMARKNET",
    arrival_date=date(2026, 10, 8),
    variety="Local",
)

options = NS(
    language="en",
    storage_days=14,
    expected_storage_loss_percent=None,
    storage_cost_per_quintal_day=8.0,
    transport_cost_per_km_tonne=42.0,
    distance_km=65.0,
    processor_price_per_quintal=None,
    handling_cost_per_quintal=35.0,
)

forecast = [
    {"predicted_price": 2100.0}
] * 30

result = RecommendationEngine().evaluate(
    batch,
    assessment,
    [market],
    forecast,
    options,
)

by_action = {
    item["action"]: item
    for item in result["alternatives"]
}

sell = by_action["SELL_NOW"]

print("=== SELL NOW ===")
print("Gross:", sell["gross_revenue"])
print("Net:", sell["net_profit"])

print()
print("=== ELIGIBILITY ===")
print("SELL_NOW:", sell["eligible"])
print("PROCESS:", by_action["PROCESS"]["eligible"])
print("STORE:", by_action["STORE"]["eligible"])
print("WAIT:", by_action["WAIT"]["eligible"])

assert sell["gross_revenue"] == 20000.0
assert sell["net_profit"] == 16920.0

assert by_action["PROCESS"]["eligible"] is False
assert by_action["STORE"]["eligible"] is False
assert by_action["WAIT"]["eligible"] is False

assert result["recommended_action"] == "SELL_NOW"

print()
print("ECONOMICS V2 SELF-CHECK: PASS")
print("1000 kg = 10 quintals")
print("10 x Rs 2000/qtl = Rs 20,000 reference gross")
print("Transport = Rs 2,730")
print("Handling = Rs 350")
print("Post-harvest net realization = Rs 16,920")
print("PROCESS blocked without processor quote")
print("STORE/WAIT blocked without storage-loss assumption")
