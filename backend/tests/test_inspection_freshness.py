from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models import MarketPrice


def test_inspection_uses_reporting_date_and_preserves_processor_quote(monkeypatch):
    monkeypatch.setattr("app.api.router.ensure_web_prices", lambda *args, **kwargs: None)
    image = Path(__file__).resolve().parents[2] / "data" / "demo-potato.jpg"
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    market = "Freshness test market"
    with TestClient(app) as client:
        with SessionLocal() as db:
            for market_name, day in [(market, today - timedelta(days=8)), ("Other market", today)]:
                db.add(MarketPrice(
                    commodity="Potato", state="Karnataka", district="Test district",
                    market=market_name, variety="Local", grade="FAQ", arrival_date=day,
                    min_price=1800, modal_price=2200, max_price=2400, source="AGMARKNET test",
                ))
            db.commit()

        created = client.post("/api/v1/batches", json={
            "quantity_kg": 1000, "source_location": "Test district", "variety": "Local",
            "state": "Karnataka", "district": "Test district", "intended_market": market,
        })
        assert created.status_code == 201, created.text
        url = f"/api/v1/batches/{created.json()['id']}"
        with image.open("rb") as file:
            uploaded = client.post(f"{url}/images", files={"files": ("potato.jpg", file, "image/jpeg")})
        assert uploaded.status_code == 201, uploaded.text

        analysis = client.post(f"{url}/analyze", json={"processor_price_per_quintal": 2500})
        assert analysis.status_code == 200, analysis.text
        result = analysis.json()
        assert result["assessment"]["feature_summary"]["market_snapshot"]["status"] == "stale"
        assert result["recommendation"]["recommended_action"] == "PROCESS"
        assert all(not option["eligible"] for option in result["recommendation"]["alternatives"] if option["action"] != "PROCESS")

        with SessionLocal() as db:
            db.add(MarketPrice(
                commodity="Potato", state="Karnataka", district="Test district",
                market=market, variety="Local", grade="FAQ", arrival_date=today,
                min_price=1800, modal_price=2200, max_price=2400, source="AGMARKNET test",
            ))
            db.commit()
        analysis = client.post(f"{url}/analyze", json={"quality_pricing_mode": "reference"})
        assert analysis.status_code == 200, analysis.text
        saved = client.get(url)
        assert saved.headers["Cache-Control"] == "no-store"
        snapshot = saved.json()["assessment"]["feature_summary"]["market_snapshot"]
        assert snapshot["status"] == "recent"
        assert snapshot["reporting_date"] == today.isoformat()
        assert saved.json()["recommendation"]["expected_selling_price"] == 2200


def test_news_refresh_reports_fallback_and_retains_headlines(monkeypatch):
    from app.api.router import news_service

    for variable in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(news_service.settings, "potato_news_feeds", "https://example.test/feed")
    feed = b"""<rss><channel><item><title>Potato mandi report</title>
    <link>https://example.test/story</link><pubDate>2026-11-11T12:00:00Z</pubDate>
    </item></channel></rss>"""
    monkeypatch.setattr(httpx.Client, "get", lambda *args, **kwargs: httpx.Response(
        200, content=feed, request=httpx.Request("GET", "https://example.test/feed"),
    ))
    with TestClient(app) as client:
        fresh = client.request("GET", "/api/v1/news?refresh=true")
        assert fresh.status_code == 200, fresh.text
        assert fresh.json()["live_data"] is True
        assert fresh.json()["articles"][0]["title"] == "Potato mandi report"
        assert fresh.json()["freshness"].endswith("+00:00")
        assert fresh.headers["Cache-Control"] == "no-store"

        def unavailable(*args, **kwargs):
            raise httpx.ConnectError("Feed unavailable")

        monkeypatch.setattr(httpx.Client, "get", unavailable)
        cached = client.request("GET", "/api/v1/news?refresh=true")
        assert cached.status_code == 200, cached.text
        assert cached.json()["live_data"] is False
        assert cached.json()["articles"][0]["title"] == "Potato mandi report"
        assert "saved headlines" in cached.json()["note"]
