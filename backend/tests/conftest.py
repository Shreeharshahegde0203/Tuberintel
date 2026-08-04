from __future__ import annotations

import os
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

TEST_ROOT = Path("/tmp/tuberintel-test-runtime")
if TEST_ROOT.exists():
    shutil.rmtree(TEST_ROOT)
TEST_ROOT.mkdir(parents=True)
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_ROOT / 'test.db'}"
os.environ["UPLOAD_DIR"] = str(TEST_ROOT / "uploads")
os.environ["ANNOTATED_DIR"] = str(TEST_ROOT / "annotated")
os.environ["MODEL_MODE"] = "cv_demo"
os.environ["INTERNAL_SERVICE_KEY"] = "test-internal-key"

from app.main import app  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.models import Batch, MarketPrice  # noqa: E402
from app.services.market_service import MarketService  # noqa: E402


def seed_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        today = date.today()
        db.add(
            Batch(
                batch_code="PV-TEST-0001",
                owner_user_id="user-1",
                variety="Kufri Jyoti",
                quantity_kg=1000,
                source_location="Kolar, Karnataka",
                state="Karnataka",
                district="Kolar",
                status="created",
            )
        )
        for offset, market_name, district, modal in [
            (0, "Kolar APMC", "Kolar", 2100),
            (0, "Binny Mill (F&V), Bengaluru", "Bengaluru", 2200),
            (1, "Kolar APMC", "Kolar", 2050),
            (1, "Binny Mill (F&V), Bengaluru", "Bengaluru", 2180),
            (2, "Hassan APMC", "Hassan", 1980),
        ]:
            db.add(
                MarketPrice(
                    state="Karnataka",
                    district=district,
                    market=market_name,
                    commodity="Potato",
                    variety="Local",
                    grade="FAQ",
                    arrival_date=today - timedelta(days=offset),
                    min_price=modal - 150,
                    max_price=modal + 180,
                    modal_price=modal,
                    source="seeded demonstration series",
                )
            )
        db.commit()
        MarketService().sync_directory(db, state="Karnataka")


@pytest.fixture()
async def client() -> AsyncClient:
    seed_database()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
