from __future__ import annotations

import os
import shutil
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parent / ".runtime"
DB_PATH = TEST_ROOT / "test.db"
if TEST_ROOT.exists():
    shutil.rmtree(TEST_ROOT)
TEST_ROOT.mkdir(parents=True)
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["UPLOAD_DIR"] = str(TEST_ROOT / "uploads")
os.environ["ANNOTATED_DIR"] = str(TEST_ROOT / "annotated")
os.environ["MODEL_MODE"] = "cv_demo"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def test_complete_batch_workflow() -> None:
    demo_image = Path(__file__).resolve().parents[2] / "data" / "demo-potato.jpg"
    assert demo_image.exists()

    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["model_mode"] == "cv_demo"

        created = client.post("/api/v1/batches", json={
            "variety": "Kufri Jyoti",
            "quantity_kg": 850,
            "farmer_name": "Demonstration Farmer",
            "source_location": "Kolar, Karnataka",
            "state": "Karnataka",
            "district": "Kolar",
            "intended_market": "Kolar APMC",
        })
        assert created.status_code == 201, created.text
        batch_id = created.json()["id"]

        with demo_image.open("rb") as image_file:
            upload = client.post(
                f"/api/v1/batches/{batch_id}/images",
                files=[("files", ("demo-potato.jpg", image_file, "image/jpeg"))],
            )
        assert upload.status_code == 201, upload.text
        assert len(upload.json()["images"]) == 1

        analyzed = client.post(f"/api/v1/batches/{batch_id}/analyze", json={
            "storage_cost_per_quintal_day": 8,
            "storage_days": 14,
            "transport_cost_per_km_tonne": 42,
            "distance_km": 65,
            "processor_price_per_quintal": None,
            "handling_cost_per_quintal": 35,
            "target_margin_percent": 10,
        })
        assert analyzed.status_code == 200, analyzed.text
        result = analyzed.json()
        assert result["status"] == "analyzed"
        assert result["assessment"]["quality_grade"] in {"A", "B", "C", "D"}
        assert 0 <= result["assessment"]["quality_score"] <= 100
        assert result["images"][0]["annotated_url"]
        assert result["recommendation"]["recommended_action"] in {"SELL_NOW", "STORE", "PROCESS", "WAIT"}
        assert len(result["recommendation"]["alternatives"]) == 4
        assert len(result["recommendation"]["decision_factors"]) >= 4
        assert {item["action"] for item in result["recommendation"]["alternatives"]} == {
            "SELL_NOW", "STORE", "PROCESS", "WAIT"
        }

        feedback = client.post(f"/api/v1/batches/{batch_id}/feedback", json={
            "action_taken": result["recommendation"]["recommended_action"],
            "actual_price_per_quintal": 2050,
            "actual_profit": 11000,
            "rating": 5,
            "notes": "Integration test outcome",
        })
        assert feedback.status_code == 201, feedback.text

        dashboard = client.get("/api/v1/dashboard")
        assert dashboard.status_code == 200
        assert dashboard.json()["analyzed_batches"] == 1

        market = client.get("/api/v1/market/overview", params={"state": "Karnataka"})
        assert market.status_code == 200
        assert market.json()["latest_prices"]
        assert market.json()["forecast"]


def test_complete_state_reference_and_database_backed_mandi_directory() -> None:
    with TestClient(app) as client:
        states = client.get('/api/v1/market/directory/states')
        assert states.status_code == 200, states.text
        payload = states.json()
        assert len(payload) == 36
        assert sum(item['type'] == 'State' for item in payload) == 28
        assert sum(item['type'] == 'Union Territory' for item in payload) == 8
        assert any(item['name'] == 'Karnataka' for item in payload)
        assert any(item['name'] == 'Ladakh' for item in payload)

        directory = client.get('/api/v1/market/directory/mandis', params={'state': 'Karnataka'})
        assert directory.status_code == 200, directory.text
        data = directory.json()
        assert data['state'] == 'Karnataka'
        assert data['count'] >= 1
        assert data['districts'] == sorted(data['districts'])
        assert all(item['state'] == 'Karnataka' for item in data['mandis'])

        filters = client.get('/api/v1/market/filters', params={'state': 'Karnataka'})
        assert filters.status_code == 200, filters.text
        filter_data = filters.json()
        assert len(filter_data['states']) == 36
        assert set(data['districts']).issubset(set(filter_data['districts']))


def test_trade_marketplace_measurement_and_grounded_assistant() -> None:
    demo_image = Path(__file__).resolve().parents[2] / "data" / "demo-potato.jpg"
    headers = {"X-User-Ref": "demo-test-user"}

    with TestClient(app) as client:
        ready = client.get("/api/v1/health/ready")
        assert ready.status_code == 200, ready.text
        assert ready.json()["database"] == "ok"

        created = client.post("/api/v1/batches", json={
            "variety": "Kufri Jyoti",
            "quantity_kg": 1200,
            "farmer_name": "Marketplace Test Farmer",
            "source_location": "Kolar, Karnataka",
            "state": "Karnataka",
            "district": "Kolar",
        })
        assert created.status_code == 201, created.text
        batch_id = created.json()["id"]

        with demo_image.open("rb") as image_file:
            upload = client.post(
                f"/api/v1/batches/{batch_id}/images",
                files=[("files", ("demo-potato.jpg", image_file, "image/jpeg"))],
            )
        assert upload.status_code == 201, upload.text

        analyzed = client.post(f"/api/v1/batches/{batch_id}/analyze", json={
            "storage_days": 10,
            "measured_length_mm": 72.0,
            "measured_width_mm": 54.0,
            "measurement_source": "manual",
        })
        assert analyzed.status_code == 200, analyzed.text
        summary = analyzed.json()["assessment"]["feature_summary"]
        assert summary["size_class"] == "M (40–59 mm)"
        assert summary["physical_measurement"]["width_mm"] == 54.0

        payload = {
            "listing_type": "SELL",
            "owner_name": "Marketplace Test Farmer",
            "contact_phone": "9999999999",
            "variety": "Will be replaced from batch",
            "quantity_kg": 1000,
            "price_per_quintal": 2300,
            "state": "Karnataka",
            "district": "Kolar",
            "location": "Kolar APMC belt",
            "notes": "Linked to analyzed lot",
            "source_batch_id": batch_id,
        }
        create_headers = {**headers, "Idempotency-Key": "test-listing-key-1"}
        listing = client.post("/api/v1/marketplace/listings", json=payload, headers=create_headers)
        assert listing.status_code == 201, listing.text
        item = listing.json()
        assert item["verified_quality"] is True
        assert item["quality_grade"] in {"A", "B", "C", "D"}
        assert item["size_class"] == "M (40–59 mm)"
        assert item["variety"] == "Kufri Jyoti"

        duplicate = client.post("/api/v1/marketplace/listings", json=payload, headers=create_headers)
        assert duplicate.status_code == 201, duplicate.text
        assert duplicate.json()["id"] == item["id"]

        favorite = client.post(f"/api/v1/marketplace/listings/{item['id']}/favorite", headers=headers)
        assert favorite.status_code == 200, favorite.text
        assert favorite.json()["favorite"] is True

        favorites = client.get("/api/v1/marketplace/listings", params={"favorites_only": True}, headers=headers)
        assert favorites.status_code == 200, favorites.text
        assert any(row["id"] == item["id"] and row["is_favorite"] for row in favorites.json()["items"])

        assistant = client.post("/api/v1/assistant/query", json={
            "message": "Should I sell this batch now or store it?",
            "language": "en",
            "batch_id": batch_id,
            "state": "Karnataka",
            "district": "Kolar",
        })
        assert assistant.status_code == 200, assistant.text
        answer = assistant.json()
        assert answer["mode"] == "local_grounded"
        assert answer["answer"]
        assert any(source["kind"] == "batch" for source in answer["sources"])

        cold = client.get("/api/v1/marketplace/cold-storage", params={"state": "Karnataka"})
        transport = client.get("/api/v1/marketplace/transport", params={"state": "Karnataka"})
        assert cold.status_code == 200 and cold.json()
        assert transport.status_code == 200 and transport.json()


def test_market_forecast_endpoint_is_operational_and_rejects_long_numeric_horizons() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/market/forecast",
            params={"state": "Karnataka", "market": "Kolar APMC", "horizon_days": 30},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert len(payload["points"]) == 30
        assert payload["points"][0]["horizon_days"] == 1
        assert payload["points"][-1]["horizon_days"] == 30
        assert payload["model_name"]
        assert payload["methodology"]
        assert all(point["lower_bound"] <= point["predicted_price"] <= point["upper_bound"] for point in payload["points"])

        too_long = client.get(
            "/api/v1/market/forecast",
            params={"state": "Karnataka", "horizon_days": 31},
        )
        assert too_long.status_code == 422


def test_market_long_horizon_is_directional_outlook_not_numeric_forecast() -> None:
    with TestClient(app) as client:
        outlook = client.get(
            "/api/v1/market/outlook",
            params={"state": "Karnataka", "horizon_days": 60},
        )
        assert outlook.status_code == 200, outlook.text
        payload = outlook.json()
        assert payload["horizon_days"] == 60
        assert payload["direction"] in {"rising", "falling", "stable", "insufficient_data"}
        assert "predicted_price" not in payload
        assert "precise" in payload["note"].lower() or "numeric" in payload["note"].lower()
