from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_states_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/market/directory/states")
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert payload[0]["name"] == "Karnataka"


@pytest.mark.anyio
async def test_districts_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/market/directory/districts", params={"state": "Karnataka"})
    assert response.status_code == 200
    districts = {item["name"] for item in response.json()}
    assert {"Kolar", "Bengaluru"}.issubset(districts)


@pytest.mark.anyio
async def test_unknown_state_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/market/directory/districts", params={"state": "Unknown"})
    assert response.status_code == 404


@pytest.mark.anyio
async def test_mandis_endpoint_pagination(client: AsyncClient) -> None:
    response = await client.get("/api/v1/market/directory/mandis", params={"state": "Karnataka", "limit": 1, "offset": 0})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert len(payload["items"]) == 1


@pytest.mark.anyio
async def test_case_insensitive_price_filtering(client: AsyncClient) -> None:
    response = await client.get("/api/v1/market/prices", params={"state": "karnataka", "district": "kolar", "latest_only": True})
    assert response.status_code == 200
    assert response.json()
    assert all(item["state"] == "Karnataka" for item in response.json())


@pytest.mark.anyio
async def test_market_filters_and_analytics(client: AsyncClient) -> None:
    filters = await client.get("/api/v1/market/filters", params={"state": "Karnataka"})
    assert filters.status_code == 200
    assert "Local" in filters.json()["varieties"]

    analytics = await client.get("/api/v1/market/analytics", params={"state": "Karnataka", "window_days": 30})
    assert analytics.status_code == 200
    assert analytics.json()["summary"]["record_count"] >= 1


@pytest.mark.anyio
async def test_batch_ownership_protection(client: AsyncClient) -> None:
    denied = await client.get("/api/v1/batches/1", headers={"Authorization": "Bearer test-token:user-2:user2@example.com:user"})
    assert denied.status_code == 403

    allowed = await client.get("/api/v1/batches/1", headers={"Authorization": "Bearer test-token:user-1:user1@example.com:user"})
    assert allowed.status_code == 200


@pytest.mark.anyio
async def test_unauthorized_sync_request(client: AsyncClient) -> None:
    response = await client.post("/api/v1/admin/market/directory/sync", params={"state": "Karnataka"})
    assert response.status_code == 403


@pytest.mark.anyio
async def test_authorized_sync_request(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/admin/market/directory/sync",
        params={"state": "Karnataka"},
        headers={"x-internal-service-key": "test-internal-key"},
    )
    assert response.status_code == 200
    assert response.json()["mandi_count"] >= 1
