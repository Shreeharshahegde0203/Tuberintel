#!/usr/bin/env python3
"""Create one immediately usable demonstration batch through the public API contract."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def main() -> None:
    image = ROOT / "data" / "demo-potato.jpg"
    with TestClient(app) as client:
        created = client.post("/api/v1/batches", json={
            "variety": "Kufri Jyoti",
            "quantity_kg": 850,
            "farmer_name": "Demonstration Farmer",
            "source_location": "Kolar, Karnataka",
            "state": "Karnataka",
            "district": "Kolar",
            "intended_market": "Kolar APMC",
        })
        created.raise_for_status()
        batch_id = created.json()["id"]
        with image.open("rb") as handle:
            uploaded = client.post(
                f"/api/v1/batches/{batch_id}/images",
                files=[("files", (image.name, handle, "image/jpeg"))],
            )
        uploaded.raise_for_status()
        analyzed = client.post(f"/api/v1/batches/{batch_id}/analyze", json={
            "storage_cost_per_quintal_day": 8,
            "storage_days": 14,
            "transport_cost_per_km_tonne": 42,
            "distance_km": 65,
            "processor_price_per_quintal": None,
            "handling_cost_per_quintal": 35,
            "target_margin_percent": 10,
        })
        analyzed.raise_for_status()
        result = analyzed.json()
        print(
            f"Created {result['batch_code']} — grade {result['assessment']['quality_grade']}, "
            f"recommended {result['recommendation']['recommended_action']}."
        )


if __name__ == "__main__":
    main()
